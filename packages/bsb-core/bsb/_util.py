import contextlib as _ctxlib
import functools as _ft
import inspect as _inspect
import itertools as _it
import os as _os
import sys as _sys
import typing as _t

import numpy as _np

ichain = _it.chain.from_iterable


class instance_cache:
    """
    Cache a method's results on the instance instead of on the function.

    :func:`functools.cache` on a method keys on ``self``, so the function's cache
    holds a strong reference to every instance it has ever been called on and none
    of them can be collected for as long as the class exists. Keeping the results on
    the instance means they are freed with it.

    The bound method exposes ``cache_clear()``, which empties the cache of that one
    instance, for values that go stale when the instance changes.

    Results are keyed on the arguments, as :func:`functools.cache` does, so the
    arguments still have to be hashable.
    """

    def __init__(self, method):
        self._method = method
        self._name = f"_cache_{method.__name__}"
        _ft.update_wrapper(self, method)

    def __set_name__(self, owner, name):
        self._name = f"_cache_{name}"

    def __get__(self, instance, owner=None):
        if instance is None:
            return self
        return _BoundInstanceCache(self._method, self._name, instance)


class _BoundInstanceCache:
    """One instance's view of an :class:`instance_cache` method."""

    def __init__(self, method, name, instance):
        self._method = method
        self._name = name
        self._instance = instance
        _ft.update_wrapper(self, method)

    def __call__(self, *args, **kwargs):
        cache = self._instance.__dict__.setdefault(self._name, {})
        key = (args, tuple(sorted(kwargs.items()))) if kwargs else args
        try:
            return cache[key]
        except KeyError:
            cache[key] = value = self._method(self._instance, *args, **kwargs)
            return value

    def cache_clear(self):
        """Forget what was cached for this instance."""
        self._instance.__dict__.pop(self._name, None)


def merge_dicts(a, b):
    """
    Merge 2 dictionaries and their subdictionaries.
    """
    for key in b:
        if key in a and isinstance(a[key], dict) and isinstance(b[key], dict):
            merge_dicts(a[key], b[key])
        else:
            a[key] = b[key]
    return a


def obj_str_insert(__str__):
    """
    Decorator to insert the return value of __str__ into '<classname {returnvalue} at
    0x...>'.
    """

    @_ft.wraps(__str__)
    def wrapper(self):
        obj_str = object.__repr__(self)
        return obj_str.replace("at 0x", f"{__str__(self)} at 0x")

    return wrapper


@_ctxlib.contextmanager
def suppress_stdout():
    """
    Context manager that attempts to silence regular stdout and stderr.

    Some binary components may yet circumvene this if they access the underlying OS's
    stdout directly, like streaming to `/dev/stdout`.
    """
    with open(_os.devnull, "w") as devnull:
        old_stdout = _sys.stdout
        old_stderr = _sys.stderr
        _sys.stdout = devnull
        _sys.stderr = devnull
        try:
            yield
        finally:
            _sys.stdout = old_stdout
            _sys.stderr = old_stderr


def get_qualified_class_name(x):
    """
    Return an object's module and class name.
    """
    if _inspect.isclass(x):
        return f"{x.__module__}.{str(x.__name__)}"
    return f"{x.__class__.__module__}.{str(x.__class__.__name__)}"


def listify_input(value):
    """
    Turn any non-list values into a list containing the value.

    Sequences will be
    converted to a list using `list()`, `None` will  be replaced by an empty list.
    """
    if value is None:
        return []
    if isinstance(value, str):
        return [str]
    try:
        return list(value)
    except Exception:
        return [value]


def sanitize_ndarray(arr_input, shape, dtype=None):
    """
    Convert an object to an ndarray and shape, avoiding to copy it wherever possible.
    """
    kwargs = {}
    if dtype is not None:
        kwargs["dtype"] = dtype
    arr = _np.asarray(arr_input, **kwargs)
    arr.shape = shape
    return arr


def assert_samelen(*args):
    """
    Assert that all input arguments have the same length.
    """
    len_ = None
    assert all(
        ((len_ := len(arg)) if len_ is None else len(arg)) == len_ for arg in args
    ), "Input arguments should be of same length."


def immutable():
    """
    Decorator to mark a method as immutable, so that any calls to it return, and are
    performed on, a copy of the instance.
    """

    def immutable_decorator(f):
        @_ft.wraps(f)
        def immutable_action(self, *args, **kwargs):
            new_instance = self.__copy__()
            f(new_instance, *args, **kwargs)
            return new_instance

        return immutable_action

    return immutable_decorator


def unique(iter_: _t.Iterable[_t.Any]):
    """
    Return a new list containing all the unique elements of an iterator.
    """
    return [*set(iter_)]


def rotation_matrix_from_vectors(vec1, vec2):
    """
    Find the rotation matrix that aligns vec1 to vec2.

    :param vec1: A 3d "source" vector
    :param vec2: A 3d "destination" vector
    :return mat: A transform matrix (3x3) which when applied to vec1, aligns it with vec2.
    """
    if (
        _np.isnan(vec1).any()
        or _np.isnan(vec2).any()
        or not _np.any(vec1)
        or not _np.any(vec2)
    ):
        raise ValueError("Vectors should not contain nan and their norm should not be 0.")
    a = (vec1 / _np.linalg.norm(vec1)).reshape(3)
    b = (vec2 / _np.linalg.norm(vec2)).reshape(3)
    v = _np.cross(a, b)
    if any(v):  # if not all zeros then
        c = _np.dot(a, b)
        s = _np.linalg.norm(v)
        kmat = _np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
        return _np.eye(3) + kmat + kmat.dot(kmat) * ((1 - c) / (s**2))
    else:
        return _np.eye(3)  # cross of all zeros only occurs on identical directions
