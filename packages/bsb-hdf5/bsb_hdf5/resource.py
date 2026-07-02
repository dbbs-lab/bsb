import contextlib
import contextvars
import functools
import inspect
import typing
import warnings

import h5py
import numpy as np

from ._telemetry import _hdf5_tracer

if typing.TYPE_CHECKING:  # pragma: nocover
    from . import HDF5Engine

# Semantic marker for things that get injected
HANDLED = None


# Per-(engine, scope) state. Value: {id(engine): (mode, h5py_handle)}.
# The default is `None` (a mutable default would be shared across all contexts);
# `_get_handles` substitutes the empty map so `.get(id(engine))` is always safe.
_engine_handle: contextvars.ContextVar = contextvars.ContextVar(
    "_bsb_hdf5_engine_handle", default=None
)


def _get_handles() -> dict:
    """Return the per-engine handle map for the current context, or the empty
    map when none is set."""
    return _engine_handle.get() or {}


class _WriteScopeState:
    """Mutable flag for :class:`UnusedWriteScopeWarning` detection."""

    __slots__ = ("wrote",)

    def __init__(self):
        self.wrote = False


_write_scope_state: contextvars.ContextVar = contextvars.ContextVar(
    "_bsb_hdf5_write_scope_state", default=None
)


class PromotedHandleWarning(UserWarning):
    """
    A write operation ran inside a read scope. mpilock promoted the read lock
    to a write for the duration of that call, briefly serializing all readers
    and writers across the cluster.

    The promotion itself is safe, but holding write locks inside read scopes
    blocks parallelism, so it's usually a refactor target (move the write
    outside the read scope). If the write is genuinely small, one-off, and
    cannot be moved, pass ``promote_from_read=True`` at the call site to
    silence this warning.
    """


class UnusedWriteScopeWarning(UserWarning):
    """
    A :meth:`~bsb_hdf5.HDF5Engine.write_scope` block exited without any
    decorated ``@handles_handles("a")`` operation running inside. The cluster-
    wide write lock was held for nothing; other writers could not proceed.

    Replace with :meth:`~bsb_hdf5.HDF5Engine.read_scope` if you only needed
    reads, or remove the scope entirely if you don't need batching.
    """


def _lookup_handle(engine, requested_mode):
    """Return an open handle on ``engine`` that satisfies ``requested_mode``,
    or ``None`` if no compatible handle is open in the current context.

    A write-mode handle satisfies both read and write requests; a read-mode
    handle only satisfies read requests. A write request encountered while a
    read scope is active returns ``None`` so the decorator opens a fresh write
    handle; mpilock promotes our held read lock to write for that block and
    returns us to the read state on release. (Hence
    :class:`PromotedHandleWarning` exists to flag the pattern.)
    """
    cur = _get_handles().get(id(engine))
    if cur is None:
        return None
    held_mode, held_handle = cur
    if requested_mode == "r":
        return held_handle
    # requested_mode == "a"
    if held_mode == "a":
        return held_handle
    return None


# Decorator to inject handles
def handles_handles(handle_type, handler=lambda args: args[0]._engine):
    """
    Decorator for :class:`~.resource.Resource` methods to lock and open hdf5
    files. The decorator does three things:

    1. If the caller passed ``handle=`` explicitly, the inner function gets
       that handle. Period.
    2. Otherwise the decorator checks the per-engine handle ContextVar (set by
       :meth:`~bsb_hdf5.HDF5Engine.read_scope` /
       :meth:`~bsb_hdf5.HDF5Engine.write_scope` or by
       any outer ``@handles_handles`` call that opened a handle). If a
       compatible handle is open, it is reused. No mpilock acquire, no
       ``h5py.File`` open.
    3. Otherwise the decorator acquires the appropriate mpilock, opens a fresh
       ``h5py.File`` in ``handle_type`` mode, registers it on the ContextVar
       so any nested ``@handles_handles`` call inherits it, runs the function,
       and tears down on exit.

    A write operation called from inside a read scope is legal (mpilock
    promotes the lock under the hood) but emits :class:`PromotedHandleWarning`
    unless the call site passes ``promote_from_read=True``.

    By default, the first argument of the decorated function should be the
    Resource. ``handler`` overrides this for static/class methods that expose
    the engine differently.
    """

    lock_f = {"r": lambda eng: eng._read, "a": lambda eng: eng._write}.get(handle_type)

    def decorator(f):
        sig = inspect.signature(f)
        if "handle" not in sig.parameters:
            raise ValueError(
                f"`{f.__module__}.{f.__name__}` needs handle to be handled by "
                f"handles_handles. Clearly."
            )

        @functools.wraps(f)
        def handle_indirection(
            *args, handle=None, promote_from_read=False, **kwargs
        ):
            engine = handler(args)

            # 1. Explicit `handle=` wins. Otherwise look up the ambient scope.
            if handle is None:
                handle = _lookup_handle(engine, handle_type)
                if handle is None and handle_type == "a":
                    # The lookup returned None for a write request. Either no
                    # scope is open (fine), or we're inside a read scope and
                    # about to trigger an mpilock promotion. Detect the second
                    # case by checking whether ANY handle is open on this
                    # engine in the current context.
                    cur = _get_handles().get(id(engine))
                    if cur is not None and not promote_from_read:
                        warnings.warn(
                            f"`{f.__module__}.{f.__name__}` is a write "
                            f"operation called from inside a read scope. "
                            f"mpilock will promote the read to a write for "
                            f"this call; every promotion briefly serializes "
                            f"all readers and writers across the cluster. "
                            f"If this is intentional and the write is small "
                            f"and one-off, pass `promote_from_read=True` at "
                            f"the call site to silence this. Otherwise, move "
                            f"the write outside the read scope.",
                            PromotedHandleWarning,
                            stacklevel=2,
                        )

            # 2. Mark the enclosing write_scope as used, if any.
            if handle_type == "a":
                state = _write_scope_state.get()
                if state is not None:
                    state.wrote = True

            _path = getattr(args[0], "_path", None)
            _attrs = {"hdf5.mode": handle_type}
            if _path is not None:
                _attrs["hdf5.path"] = _path
            with _hdf5_tracer.trace(f"hdf5.{f.__name__}", attributes=_attrs):
                try:
                    bound = sig.bind(*args, **kwargs)
                except TypeError:
                    # Re-call the actual function, for better TypeError
                    try:
                        f(*args, **kwargs)
                    except TypeError as e:
                        # Re-raise the exception from None for better stack trace
                        raise e from None
                # The wrapper captures `handle` as its own keyword-only
                # parameter, so any handle we resolved above is NOT in
                # `bound.arguments`. Inject it before calling f.
                if handle is not None:
                    bound.arguments["handle"] = handle
                    return f(*bound.args, **bound.kwargs)

                # 3. No handle to reuse: open one and register on the ContextVar
                # so nested calls inherit it. The `with lock()` block does the
                # mpilock promotion under the hood when we're inside a read
                # scope and `handle_type == "a"`.
                with lock_f(engine)(), engine._handle(handle_type) as new_handle:
                    bound.arguments["handle"] = new_handle
                    current = _get_handles()
                    tok = _engine_handle.set(
                        {**current, id(engine): (handle_type, new_handle)}
                    )
                    try:
                        return f(*bound.args, **bound.kwargs)
                    finally:
                        _engine_handle.reset(tok)

        return handle_indirection

    return decorator


@contextlib.contextmanager
def _push_scope(engine, mode):
    """Open a handle on ``engine`` in ``mode``, push it onto the engine-handle
    ContextVar, and yield the handle. Used by
    :meth:`~bsb_hdf5.HDF5Engine.read_scope` and
    :meth:`~bsb_hdf5.HDF5Engine.write_scope`. Also installs a
    :class:`_WriteScopeState` on the ``_write_scope_state`` ContextVar when
    ``mode == "a"`` so :class:`UnusedWriteScopeWarning` can fire on exit.
    """
    lock_f = {"r": lambda eng: eng._read, "a": lambda eng: eng._write}[mode]
    with lock_f(engine)(), engine._handle(mode) as handle:
        current = _get_handles()
        engine_tok = _engine_handle.set({**current, id(engine): (mode, handle)})
        scope_tok = None
        state = None
        if mode == "a":
            state = _WriteScopeState()
            scope_tok = _write_scope_state.set(state)
        try:
            yield handle
        finally:
            _engine_handle.reset(engine_tok)
            if scope_tok is not None:
                _write_scope_state.reset(scope_tok)
            if state is not None and not state.wrote:
                warnings.warn(
                    "`engine.write_scope()` opened but no @handles_handles('a') "
                    "operation ran inside. The cluster-wide write lock was held "
                    "unnecessarily. Use `read_scope()` if you only need reads, "
                    "or drop the scope and let individual decorated calls open "
                    "their own short-lived handles.",
                    UnusedWriteScopeWarning,
                    stacklevel=3,
                )


def handles_static_handles(handle_type):
    """
    Decorator for static methods to lock and open hdf5 files.

    The :class:`~bsb.storage.interfaces.Engine` handler is expected to be the first
    argument of the decorated function.
    """
    return handles_handles(handle_type, handler=lambda args: args[0])


def handles_class_handles(handle_type):
    """
    Decorator for class methods to lock and open hdf5 files.

    The :class:`~bsb.storage.interfaces.Engine` handler is expected to be the second
    argument of the decorated function.
    """
    return handles_handles(handle_type, handler=lambda args: args[1])


class Resource:
    def __init__(self, engine: "HDF5Engine", path: str):
        self._engine: HDF5Engine = engine
        self._path = path

    def __eq__(self, other):
        return (
            self._engine == getattr(other, "_engine", None) and self._path == other._path
        )

    def require(self, handle):
        return handle.require_group(self._path)

    def create(self, data, *args, **kwargs):
        with (
            _hdf5_tracer.trace(
                "hdf5.create", attributes={"hdf5.path": self._path, "hdf5.mode": "a"}
            ),
            self._engine._write(),
            self._engine._handle("a") as f,
        ):
            f.create_dataset(self._path, data=data, *args, **kwargs)  # noqa: B026

    def keys(self):
        with (
            _hdf5_tracer.trace(
                "hdf5.keys", attributes={"hdf5.path": self._path, "hdf5.mode": "r"}
            ),
            self._engine._read(),
            self._engine._handle("r") as f,
        ):
            node = f[self._path]
            if isinstance(node, h5py.Group):
                return list(node.keys())

    def remove(self):
        with (
            _hdf5_tracer.trace(
                "hdf5.remove", attributes={"hdf5.path": self._path, "hdf5.mode": "a"}
            ),
            self._engine._write(),
            self._engine._handle("a") as f,
        ):
            del f[self._path]

    def get_dataset(self, selector=()):
        with (
            _hdf5_tracer.trace(
                "hdf5.get_dataset", attributes={"hdf5.path": self._path, "hdf5.mode": "r"}
            ),
            self._engine._read(),
            self._engine._handle("r") as f,
        ):
            return f[self._path][selector]

    @property
    def attributes(self):
        with (
            _hdf5_tracer.trace(
                "hdf5.attributes", attributes={"hdf5.path": self._path, "hdf5.mode": "r"}
            ),
            self._engine._read(),
            self._engine._handle("r") as f,
        ):
            return dict(f[self._path].attrs)

    def get_attribute(self, name):
        attrs = self.attributes
        if name not in attrs:
            raise AttributeError(f"Attribute '{name}' not found in '{self._path}'")
        return attrs[name]

    def exists(self):
        with (
            _hdf5_tracer.trace(
                "hdf5.exists", attributes={"hdf5.path": self._path, "hdf5.mode": "r"}
            ),
            self._engine._read(),
            self._engine._handle("r") as f,
        ):
            return self._path in f

    def unmap(self, selector=(), mapping=lambda m, x: m[x], data=None):
        if data is None:
            data = self.get_dataset(selector)
        map = self.get_attribute("map")
        unmapped = []
        for record in data:
            unmapped.append(mapping(map, record))
        return np.array(unmapped)

    def unmap_one(self, data, mapping=None):
        if mapping is None:
            return self.unmap(data=[data])
        else:
            return self.unmap(data=[data], mapping=mapping)

    def __iter__(self):
        return iter(self.get_dataset())

    @property
    def shape(self):
        with (
            _hdf5_tracer.trace(
                "hdf5.shape", attributes={"hdf5.path": self._path, "hdf5.mode": "r"}
            ),
            self._engine._read(),
            self._engine._handle("r") as f,
        ):
            return f[self._path].shape

    def __len__(self):
        return self.shape[0]

    def append(self, new_data, dtype=float):
        if type(new_data) is not np.ndarray:
            new_data = np.array(new_data)
        with (
            _hdf5_tracer.trace(
                "hdf5.append",
                attributes={
                    "hdf5.path": self._path,
                    "hdf5.mode": "a",
                    "hdf5.rows_added": len(new_data),
                },
            ),
            self._engine._write(),
            self._engine._handle("a") as f,
        ):
            try:
                d = f[self._path]
            except Exception:
                shape = list(new_data.shape)
                shape[0] = None
                f.create_dataset(
                    self._path, data=new_data, dtype=dtype, maxshape=tuple(shape)
                )
            else:
                len_ = d.shape[0]
                len_ += len(new_data)
                d.resize(len_, axis=0)
                d[-len(new_data) :] = new_data
