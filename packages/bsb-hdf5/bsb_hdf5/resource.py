import functools
import inspect
import typing

import h5py
import numpy as np

from ._telemetry import _hdf5_tracer

if typing.TYPE_CHECKING:  # pragma: nocover
    from . import HDF5Engine

# Semantic marker for things that get injected
HANDLED = None


# Decorator to inject handles
def handles_handles(handle_type, handler=lambda args: args[0]._engine):
    """
    Decorator for :class:`~.resource.Resource` methods to lock and open hdf5 files.

    By default, the first argument of the decorated function should be the Resource.
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
        def handle_indirection(*args, handle=None, **kwargs):
            engine = handler(args)
            lock = lock_f(engine)
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
                if bound.arguments.get("handle", None) is None:
                    with lock(), engine._handle(handle_type) as handle:
                        bound.arguments["handle"] = handle
                        return f(*bound.args, **bound.kwargs)
                else:
                    return f(*bound.args, **bound.kwargs)

        return handle_indirection

    return decorator


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
