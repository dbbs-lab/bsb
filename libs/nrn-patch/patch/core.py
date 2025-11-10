import typing
from typing import Union

from .exceptions import NotConnectableError
from .version import get_neuron_version

if typing.TYPE_CHECKING:  # pragma: nocover
    import neuron.hoc


def transform(obj):
    """
    Transform an object to its NEURON representation, if the ``__neuron__`` magic method
    is present.
    """
    if hasattr(obj, "__neuron__"):
        return obj.__neuron__()
    return obj


def transform_netcon(obj):
    """
    Transform an object into the pointer that should be connected, if the ``__netcon__``
    magic method is present.
    """
    if hasattr(obj, "__netcon__"):
        return obj.__netcon__()
    return transform(obj)


def transform_record(obj):
    """
    Transform an object into the pointer that should be recorded, if the ``__record__``
    magic method is present.
    """
    if hasattr(obj, "__record__"):
        return obj.__record__()
    return transform(obj)


def transform_arc(obj, *args, **kwargs):
    """
    Get an arclength object on a NEURON object.

    Calls the ``__arc__`` magic method
    on the callable object if present, otherwise returns the transformed object.
    """
    if hasattr(obj, "__arc__"):
        return transform(obj(obj.__arc__(*args, **kwargs)))
    else:
        return transform(obj)


def _is_sequence(obj):
    t = type(obj)
    return hasattr(t, "__len__") and hasattr(t, "__getitem__")


def assert_connectable(obj, label=None):
    """
    Assert whether an object could be used as a :class:`~.objects.Connectable`.

    :param label: Optional label to display to describe the object if the assertion fails.
    :type label: str
    """
    if not hasattr(obj, "_connections"):
        raise NotConnectableError(
            (label if label is not None else str(obj))
            + " is not connectable."
            + "It lacks attribute `_connections` required to form NetCons."
        )


def is_section(obj):
    """
    Check if an object is a section.
    """
    cls = type(transform(obj))
    return cls.__module__ == "nrn" and cls.__name__ == "Section"


def is_segment(obj):
    """
    Check if an object is a segment.
    """
    cls = type(transform(obj))
    return cls.__module__ == "nrn" and cls.__name__ == "Segment"


def is_nrn_scalar(obj):
    nv = get_neuron_version()
    cls = type(transform(obj))
    if cls.__module__ != "hoc" or cls.__name__ != "HocObject":
        return False
    try:
        if nv < "9.0a0":
            return "pointer to hoc scalar" in str(obj)
        else:
            return str(obj).startswith("data_handle<")
    except Exception:
        return False


def is_point_process(obj: Union[str, "neuron.hoc.HocObject"]):
    """
    Check if obj is a (name of a) PointProcess on the ``HocInterpreter``.

    :param obj: HocObject or name of the PointProcess to look for. Needs to be a known
      attribute of ``neuron.h``.
    :rtype: bool
    """
    from neuron import h, hoc

    try:
        if not isinstance(obj, hoc.HocObject):
            obj = getattr(h, obj)
    except Exception:
        return False
    return all(k in dir(obj) for k in ["get_loc", "has_loc", "loc", "get_segment"])


def is_density_mechanism(obj: Union[str, "neuron.hoc.HocObject"]):
    """
    Check if obj is a (name of a) DensityMechanism on the ``HocInterpreter``.

    :param obj: HocObject or name of the DensityMechanism to look for. Needs to be a known
      attribute of ``neuron.h``.
    :rtype: bool
    """
    import nrn
    from neuron import h, hoc

    if isinstance(obj, nrn.Mechanism):
        return True
    try:
        if not isinstance(obj, hoc.HocObject):
            obj = getattr(h, obj)
        hname = str(obj)
        return "neuron.DensityMechanism" in hname
    except TypeError as e:
        return "mechanism" in str(e)
    except Exception:
        return False
