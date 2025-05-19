"""
Quality of life patch for the NEURON simulator.
"""

try:
    from functools import cache, cached_property
except ImportError:  # pragma: nocover
    import functools

    def cached_property(f):
        return property(functools.lru_cache()(f))

    functools.cache = cache = functools.lru_cache()
    functools.cached_property = cached_property

from .core import (
    is_density_mechanism,
    is_nrn_scalar,
    is_point_process,
    is_section,
    is_segment,
    transform,
    transform_arc,
    transform_netcon,
    transform_record,
)
from .exceptions import NotConnectableError, NotConnectedError
from .interpreter import PythonHocInterpreter

p: "PythonHocInterpreter"
h: "PythonHocInterpreter"


def __getattr__(attr):
    if attr == "p" or attr == "h":
        return _get_interpreter()
    else:
        raise AttributeError(f"module {__name__} has no attribute {attr}.")


@cache
def _get_interpreter():
    p = PythonHocInterpreter()
    PythonHocInterpreter._process_registration_queue()
    return p


def connection(source, target, strict=True):
    if not hasattr(source, "_connections"):
        raise NotConnectableError(
            f"Source {source} is not connectable. It lacks attribute _connections "
            "required to form NetCons."
        )
    if not hasattr(target, "_connections"):
        raise NotConnectableError(
            f"Target {target} is not connectable. It lacks attribute _connections "
            "required to form NetCons."
        )
    reverse = source in target._connections
    if target not in source._connections:
        if reverse and not strict:
            return target._connections[source]
        raise NotConnectedError("Source is not connected to target.")
    return source._connections[target]


__all__ = [
    "connection",
    "h",
    "is_density_mechanism",
    "is_nrn_scalar",
    "is_point_process",
    "is_section",
    "is_segment",
    "p",
    "PythonHocInterpreter",
    "transform",
    "transform_arc",
    "transform_netcon",
    "transform_record",
]
