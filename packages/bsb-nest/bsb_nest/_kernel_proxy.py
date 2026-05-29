"""
Out-of-process NEST kernel proxy.

Runs NEST in an independent subprocess (see :mod:`._kernel_server`) and talks to
it over a :mod:`multiprocessing.connection` pipe, so the main process can query
``GetDefaults`` / ``Install`` / ``Models`` during configuration building without
mutating an in-process NEST kernel.

The subprocess is launched by file path, not forked or
:mod:`multiprocessing`-spawned: it never inherits the parent's NEST/MPI state
and never re-imports the parent's ``__main__``, and it imports ``nest`` only on
its own main thread. A third party may therefore ``import nest`` before importing
the BSB without affecting the kernel subprocess.

The proxy is created lazily on first call to :func:`get_nest_kernel_proxy`,
stored on the active :class:`~bsb.config.BuildContext` at ``ctx.bsb_nest.kernel``,
and shut down by a cleanup callback when the build context exits.
"""

import contextlib
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from multiprocessing.connection import Client

from bsb import ConfigurationError, TypeHandler, warn
from bsb.config import get_config_build_context
from bsb.config._attrs import _hasattr

from .exceptions import KernelWarning, NestKernelError

_SERVER_SCRIPT = os.path.join(os.path.dirname(__file__), "_kernel_server.py")


class _KernelProxy:
    """Parent-side handle to the kernel subprocess.

    Mirrors :class:`bsb_nest._kernel_server._Kernel`, forwarding each call over
    the connection and re-raising errors the server reports.
    """

    def __init__(self, conn):
        self._conn = conn

    def _call(self, method, *args):
        self._conn.send((method, args))
        status, payload = self._conn.recv()
        if status == "ok":
            return payload
        name, _errorname, message = payload
        raise NestKernelError(f"NEST kernel error in `{method}` ({name}): {message}")

    def install(self, module):
        return self._call("install", module)

    def load_modules(self, modules):
        return self._call("load_modules", list(modules))

    def has_delay(self, model):
        return self._call("has_delay", model)

    def models(self, mtype=None):
        return self._call("models", mtype)


def _connect_kernel():
    """Launch the kernel subprocess and connect to it.

    Returns ``(proxy, shutdown)``. Tests patch this to run the kernel in-process.
    """
    authkey = secrets.token_bytes(16)
    tmpdir = tempfile.mkdtemp(prefix="bsb-nest-kernel-")
    address = os.path.join(tmpdir, "kernel.sock")
    env = {**os.environ, "_BSB_NEST_KERNEL_AUTHKEY": authkey.hex()}
    # Launch by file path so the child neither imports bsb_nest (and thus nest)
    # at the wrong time nor re-imports the parent's __main__.
    proc = subprocess.Popen(
        [sys.executable, _SERVER_SCRIPT, address],
        stdout=subprocess.DEVNULL,
        env=env,
    )
    conn = _connect_with_retry(address, authkey, proc)

    def shutdown():
        _shutdown_kernel(proc, conn, tmpdir)

    return _KernelProxy(conn), shutdown


def _connect_with_retry(address, authkey, proc, timeout=60.0):
    deadline = time.monotonic() + timeout
    while True:
        if proc.poll() is not None:
            raise NestKernelError(
                f"NEST kernel subprocess exited with code {proc.returncode}"
                " before accepting a connection."
            )
        try:
            return Client(address, authkey=authkey)
        except (FileNotFoundError, ConnectionRefusedError):
            if time.monotonic() > deadline:
                proc.terminate()
                raise NestKernelError(
                    f"NEST kernel subprocess did not start within {timeout:g}s."
                ) from None
            time.sleep(0.02)


def _shutdown_kernel(proc, conn, tmpdir):
    with contextlib.suppress(EOFError, OSError):
        conn.send(("__stop__", ()))
        conn.recv()
    with contextlib.suppress(OSError):
        conn.close()
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    shutil.rmtree(tmpdir, ignore_errors=True)


def get_nest_kernel_proxy():
    """
    Return a proxy to the out-of-process NEST kernel for this build.

    Returns ``None`` when called outside an active configuration build; callers
    should treat that as "can't reach the kernel" and fall back gracefully.
    """
    ctx = get_config_build_context()
    if ctx is None:
        return None
    # `ctx.bsb_nest` auto-vivifies the namespace; the leaf read goes via
    # __dict__ so a missing kernel stays missing (auto-vivify would otherwise
    # return an empty namespace and mask the "not yet started" state).
    ns = ctx.bsb_nest
    existing = ns.__dict__.get("kernel")
    if existing is not None:
        return existing
    proxy, shutdown = _connect_kernel()
    ns.kernel = proxy
    ctx.add_cleanup(shutdown)
    return proxy


def load_simulation_modules(node, proxy):
    """Install a config *node*'s enclosing simulation modules into the *proxy*.

    Walks up from *node* to the owning simulation (the first ancestor that
    declares a ``modules`` attribute) and hands its ``modules`` to
    ``proxy.load_modules``, which installs each module only once per build.
    Raises :class:`~bsb.exceptions.ConfigurationError` if a module can't be
    found. No-op when *node* has no enclosing simulation, e.g. a model built in
    isolation.

    The simulation's ``modules`` must already be built when this runs; the
    attribute build order guarantees it precedes the cell and connection models
    (see :func:`bsb.config._make.get_config_attributes`). Should that order ever
    change, raise rather than silently validate models against a kernel that is
    missing the simulation's modules.
    """
    parent = getattr(node, "_config_parent", None)
    while parent is not None:
        if "modules" in getattr(type(parent), "_config_attrs", {}):
            if not _hasattr(parent, "modules"):
                raise ConfigurationError(
                    f"Cannot load the NEST modules of {parent.get_node_name()}:"
                    " its `modules` attribute is not built yet. Cell and"
                    " connection models are validated against the simulation's"
                    " modules, so the `modules` attribute must appear before"
                    " `cell_models` and `connection_models` in the simulation"
                    " config object."
                )
            missing = proxy.load_modules(list(parent.modules or []))
            if missing:
                raise ConfigurationError(
                    f"NEST module(s) not found: {', '.join(missing)}."
                )
            return
        parent = getattr(parent, "_config_parent", None)


class NestModelTypeHandler(TypeHandler):
    """Validate a NEST model name against the build's out-of-process kernel.

    Subclasses set :attr:`mtype` (the NEST model class, ``"nodes"`` or
    ``"synapses"``) and :attr:`kind` (used in messages). An unknown model is a
    hard :class:`~bsb.exceptions.ConfigurationError` when the kernel is
    reachable; when it can't be reached the name passes through and the real
    error surfaces later at ``nest.Create`` time.
    """

    mtype = None
    kind = "model"

    def __call__(self, value, _key=None, _parent=None):
        value = str(value)
        try:
            proxy = get_nest_kernel_proxy()
            if proxy is None:
                return value
            load_simulation_modules(_parent, proxy)
            models = proxy.models(mtype=self.mtype)
        except ConfigurationError:
            raise
        except Exception as e:
            warn(f"Could not validate {self.kind} model '{value}': {e}", KernelWarning)
            return value
        if value not in models:
            raise ConfigurationError(f"Unknown {self.kind} model '{value}'.")
        return value

    @property
    def __name__(self):  # pragma: nocover
        return f"nest {self.kind} model"

    def __inv__(self, value):
        return value
