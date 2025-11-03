import sys
import warnings

from opentelemetry import trace


def in_notebook():
    try:
        from IPython import get_ipython

        if "IPKernelApp" not in get_ipython().config:  # pragma: nocover
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
    if (not rank and nodes is None) or all_nodes or (nodes is not None and rank in nodes):  # noqa: SIM102
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


__all__ = [
    "report",
    "warn",
]
