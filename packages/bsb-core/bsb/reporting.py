import functools
import importlib.metadata
import inspect
import json
import sys
import warnings

from opentelemetry import trace


def in_notebook():
    try:
        from IPython import get_ipython

        if "IPKernelApp" not in get_ipython().config:  # pragma: no cover
            return False
    except ImportError:
        return False
    except AttributeError:
        return False
    return True


def in_pytest():
    return "pytest" in sys.modules


def report(*message, level=2, ongoing=False, nodes=None, all_nodes=False):
    """
    Send a message to the appropriate output channel.

    :param message: Text message to send.
    :type message: str
    :param level: Verbosity level of the message.
    :type level: int
    :param ongoing: The message is part of an ongoing progress report.
    :type ongoing: bool
    """
    from . import options
    from .services import MPI

    message = " ".join(map(str, message))
    rank = MPI.get_rank()
    trace.get_current_span().add_event(message, attributes={"mpi.rank": rank})
    if (not rank and nodes is None) or all_nodes or (nodes is not None and rank in nodes):
        if options.verbosity >= level:
            print(message, end="\n" if not ongoing else "\r", flush=True)


def warn(message, category=None, stacklevel=2, log_exc=None):
    """
    Send a warning.

    :param message: Warning message
    :type message: str
    :param category: The class of the warning.
    """
    from . import options
    from .services import MPI

    if log_exc:
        import traceback

        from .storage._util import cache

        log = (
            f"{message}\n\n"
            f"{traceback.format_exception(type(log_exc), log_exc, log_exc.__traceback__)}"
        )
        # todo: This can be removed in favor of sending the full exception to OTel.
        id = cache.files.store(log)
        path = cache.files.id_to_file_path(id)
        trace.get_current_span().add_event(
            message, attributes={"mpi.rank": MPI.get_rank(), "log.file.path": path}
        )
        message += f" See '{path}' for full error log."

    # Avoid infinite loop looking up verbosity when verbosity option is broken.
    if "Error retrieving option 'verbosity'" in message or options.verbosity > 0:
        warnings.warn(message, category, stacklevel=stacklevel)


_otel_tracer = trace.get_tracer("bsb", str(importlib.metadata.version("bsb-core")))


def _instrument_command(cls):
    _orig_handler = cls.handler

    @functools.wraps(cls.handler)
    def handler(self, context):
        attributes = {
            "bsb.type": "command_handler",
            "bsb.command_class": cls.__name__,
            "bsb.command_name": cls.name,
        }

        if hasattr(cls, "get_options"):
            attributes["bsb.command_options"] = [
                f"{k}={getattr(context, k)}" for k, v in self.get_options().items()
            ]

        with _otel_tracer.start_as_current_span(
            cls.name,
            attributes=attributes,
        ):
            return _orig_handler(self, context)

    cls.handler = handler
    return cls


def _get_implemented_abstracts(cls):
    """Return dict mapping base class → set of abstract methods implemented in cls."""
    result = {}
    subclass_abstracts = getattr(cls, "__abstractmethods__", frozenset())
    for base in cls.__mro__:
        if not hasattr(base, "__abstractmethods__"):
            continue
        base_abstracts = base.__abstractmethods__
        # Abstract methods from this base that are now implemented in cls
        implemented = base_abstracts - subclass_abstracts
        if implemented:
            result[base] = implemented
    return result


def _instrument_node(cls):
    for base, implemented in _get_implemented_abstracts(cls).items():
        for attr in implemented:
            orig_method = getattr(cls, attr)
            if inspect.isfunction(orig_method):
                wrapped = _make_otel_handler(cls, base, attr, orig_method)
                setattr(cls, attr, wrapped)


def _make_otel_handler(cls, base, attr, orig_method):
    """Return a wrapper function for a single method."""

    @functools.wraps(orig_method)
    def handler(self, *args, **kwargs):
        with _otel_tracer.start_as_current_span(
            f"{cls.__name__}.{attr}",
            attributes={
                "bsb.type": "component_method",
                "bsb.component_type": base.__name__,
                "bsb.component_class": cls.__name__,
                "bsb.component_method": attr,
                "bsb.component_attributes": json.dumps(self.__tree__()),
            },
        ):
            return orig_method(self, *args, **kwargs)

    return handler


__all__ = [
    "report",
    "warn",
]
