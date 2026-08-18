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

A kernel cannot unload a dynamically loaded module, and ``ResetKernel`` does not
remove installed modules either, so a single kernel that served one simulation
keeps that simulation's modules available to every later query. To validate each
simulation against only its own modules, the kernel is isolated per simulation:
when validation moves to a different simulation than the one the current kernel
was loaded for, the current kernel is torn down and a fresh one is spawned (see
:func:`load_simulation_modules`).
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
    # The kernel is a single, uninstrumented NEST process. Strip the MPI
    # launcher's environment so the child's `import nest` does not block trying
    # to enroll in the parent's MPI job, and disable OpenTelemetry so the
    # auto-instrumentation does not run in the child.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("OMPI_", "PMI_", "PMIX_", "OTEL_"))
    }
    env["_BSB_NEST_KERNEL_AUTHKEY"] = authkey.hex()
    env["OTEL_SDK_DISABLED"] = "true"
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


def _spawn_kernel(ctx):
    """Spawn a fresh kernel for *ctx* and store it on ``ctx.bsb_nest``.

    Registers a cleanup that tears down whichever kernel is current when the
    build exits, so a respawned kernel does not leak the previous subprocess and
    the final kernel is always shut down.
    """
    ns = ctx.bsb_nest
    proxy, shutdown = _connect_kernel()
    ns.kernel = proxy
    ns.__dict__["kernel_shutdown"] = shutdown
    return proxy


def _teardown_kernel(ctx):
    """Shut down the kernel currently stored on *ctx*, if any, and forget it."""
    ns = ctx.bsb_nest
    shutdown = ns.__dict__.pop("kernel_shutdown", None)
    ns.__dict__.pop("kernel", None)
    ns.__dict__.pop("kernel_sim", None)
    if shutdown is not None:
        shutdown()


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
    proxy = _spawn_kernel(ctx)
    # Tear down whichever kernel is current at build exit. `_teardown_kernel`
    # reads the live `ctx.bsb_nest`, so a respawn that replaces the kernel does
    # not leak the old subprocess and the final kernel is still shut down.
    ctx.add_cleanup(lambda: _teardown_kernel(ctx))
    return proxy


def _enclosing_simulation(node):
    """Return *node*'s owning simulation, the first ancestor declaring
    ``modules``, or ``None`` for a model built in isolation."""
    parent = getattr(node, "_config_parent", None)
    while parent is not None:
        if "modules" in getattr(type(parent), "_config_attrs", {}):
            return parent
        parent = getattr(parent, "_config_parent", None)
    return None


def load_simulation_modules(node, proxy):
    """Install a config *node*'s enclosing simulation modules into the *proxy*.

    Walks up from *node* to the owning simulation (the first ancestor that
    declares a ``modules`` attribute) and hands its ``modules`` to
    ``proxy.load_modules``. Raises
    :class:`~bsb.exceptions.ConfigurationError` if a module can't be found.
    No-op when *node* has no enclosing simulation, e.g. a model built in
    isolation.

    Each simulation is validated against a kernel carrying only its own modules.
    The kernel keeps every module it installs for the lifetime of its
    subprocess, so when validation moves to a different simulation than the one
    the current kernel was loaded for, that kernel is torn down and a fresh one
    is spawned before the new simulation's modules are installed. Repeated
    validations within the same simulation reuse the same kernel. The served
    simulation is keyed by ``id`` of the simulation node: that node is held by
    the config tree for the whole build, so its identity is stable and not
    reused, whereas a name or path can be empty or collide across configs built
    in one context.

    The simulation's ``modules`` must already be built when this runs; the
    attribute build order guarantees it precedes the cell and connection models
    (see :func:`bsb.config._make.get_config_attributes`). Should that order ever
    change, raise rather than silently validate models against a kernel that is
    missing the simulation's modules.
    """
    parent = _enclosing_simulation(node)
    if parent is None:
        return
    if not _hasattr(parent, "modules"):
        raise ConfigurationError(
            f"Cannot load the NEST modules of {parent.get_node_name()}:"
            " its `modules` attribute is not built yet. Cell and"
            " connection models are validated against the simulation's"
            " modules, so the `modules` attribute must appear before"
            " `cell_models` and `connection_models` in the simulation"
            " config object."
        )
    ctx = get_config_build_context()
    if ctx is not None:
        ns = ctx.bsb_nest
        sim_key = id(parent)
        if ns.__dict__.get("kernel") is proxy and ns.__dict__.get("kernel_sim") not in (
            None,
            sim_key,
        ):
            # The current kernel was loaded for a different simulation; its
            # modules cannot be unloaded, so replace it with a clean kernel.
            _teardown_kernel(ctx)
            proxy = _spawn_kernel(ctx)
        ns.__dict__["kernel_sim"] = sim_key
    missing = proxy.load_modules(list(parent.modules or []))
    if missing:
        raise ConfigurationError(f"NEST module(s) not found: {', '.join(missing)}.")
    return proxy


_UNREACHABLE = object()


def query_kernel(node, query, *, fallback, error_context, unreachable_warning=None):
    """Run ``query(proxy)`` against the build's out-of-process NEST kernel.

    Acquires the build's kernel proxy, installs *node*'s enclosing simulation
    modules, then returns ``query(proxy)``. Returns *fallback* when the kernel
    can't be reached (no active build, spawn failure, IPC error), emitting
    *unreachable_warning* if given. A :class:`~bsb.exceptions.ConfigurationError`
    from the query or from module loading propagates; any other kernel error
    warns *error_context* and returns *fallback*.
    """
    try:
        proxy = get_nest_kernel_proxy()
        if proxy is None:
            if unreachable_warning:
                warn(unreachable_warning, KernelWarning)
            return fallback
        # Loading a different simulation's modules may respawn the kernel, so
        # query whichever proxy comes back rather than the one acquired above.
        proxy = load_simulation_modules(node, proxy) or proxy
        return query(proxy)
    except ConfigurationError:
        raise
    except Exception as e:
        warn(f"{error_context}: {e}", KernelWarning)
        return fallback


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
        models = query_kernel(
            _parent,
            lambda proxy: proxy.models(mtype=self.mtype),
            fallback=_UNREACHABLE,
            error_context=f"Could not validate {self.kind} model '{value}'",
        )
        if models is _UNREACHABLE:
            return value
        if value not in models:
            raise ConfigurationError(f"Unknown {self.kind} model '{value}'.")
        return value

    @property
    def __name__(self):  # pragma: nocover
        return f"nest {self.kind} model"

    def __inv__(self, value):
        return value
