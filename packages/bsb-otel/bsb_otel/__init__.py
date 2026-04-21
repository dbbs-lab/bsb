"""
BSB OpenTelemetry integration package.
"""

import importlib.metadata
import signal

from bsb.services import MPI
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, get_current_span, set_span_in_context


class _SpanContextManagerProxy:
    """
    Proxy for the span context manager returned by tracer.start_as_current_span,
    which has been modified to be safe to re-enter.
    """

    def __init__(self, manager, span):
        self._manager = manager
        self._span = span

    def __enter__(self):
        return self._span

    def __exit__(self, *args, **kwargs):
        return self._manager.__exit__(*args, **kwargs)

    def __getattr__(self, name):
        return getattr(self._manager, name)


_tracer_registry: dict[str, "BsbTracer"] = {}


class BsbTracer:
    """
    Per-package BSB tracer. Wraps an OpenTelemetry tracer and adds MPI-aware
    span creation. Obtain an instance via :func:`get_bsb_tracer`.
    """

    def __init__(self, name: str, version: str, otel_tracer):
        self._name = name
        self._version = version
        self._otel_tracer = otel_tracer

    def trace(self, name, attributes=None):
        """
        Start a new telemetry span. Use as a context manager.

        When there is no active parent span and MPI is in use, the root span is
        automatically broadcast to all ranks so their child spans share the same
        trace. When called within an existing span, a regular child span is created.

        :param str name: name of the span
        :param dict attributes: OpenTelemetry attributes
        :returns: OpenTelemetry span context manager.
        """
        if attributes is None:
            attributes = {}

        attributes["mpi.rank"] = rank = MPI.get_rank()
        attributes["mpi.size"] = MPI.get_size()

        if not get_current_span().get_span_context().is_valid:
            if rank == 0:
                parent_span_ctx_mgr = self._otel_tracer.start_as_current_span(
                    name, attributes=attributes
                )
                parent_span = parent_span_ctx_mgr.__enter__()
                set_span_in_context(parent_span)
                parent_span_context = parent_span.get_span_context()
                MPI.bcast(parent_span_context, root=0)
                return _SpanContextManagerProxy(parent_span_ctx_mgr, parent_span)
            else:
                parent_span_context = MPI.bcast(None, root=0)
                return trace.use_span(
                    NonRecordingSpan(parent_span_context), end_on_exit=False
                )

        return self._otel_tracer.start_as_current_span(name, attributes=attributes)


def get_bsb_tracer(package_name: str, version: str = None) -> BsbTracer:
    """
    Return the :class:`BsbTracer` for *package_name*, creating and registering
    it on first call.

    :param str package_name: package name (used as the OTel instrumentation scope)
    :param str version: override the version; defaults to the installed package version
    :returns: :class:`BsbTracer`
    """
    if package_name not in _tracer_registry:
        if version is None:
            version = importlib.metadata.version(package_name)
        otel_tracer = trace.get_tracer(package_name, version)
        _tracer_registry[package_name] = BsbTracer(package_name, version, otel_tracer)
    return _tracer_registry[package_name]


class TerminationError(SystemExit):
    """
    Raised by the SIGTERM handler installed by :func:`ensure_spans_on_exit`.

    Subclasses :exc:`SystemExit` so that Python unwinds the call stack normally
    (calling ``__exit__`` on any active span context managers and ending spans),
    and then runs :mod:`atexit` handlers before the process terminates.
    """


def _sigterm_handler(signum, frame):
    raise TerminationError(f"Terminated by signal {signum}")


def ensure_spans_on_exit():
    """
    Install a SIGTERM handler that raises :exc:`TerminationError`.

    When SIGTERM is received, the running call stack is unwound cleanly: any
    active ``with tracer.trace(...)`` blocks have their ``__exit__`` called,
    spans are ended and exported, and :mod:`atexit` handlers fire before the
    process exits.

    Call this once at process startup (e.g. in your ``__main__`` entry point or
    CLI bootstrap) to ensure telemetry is not lost when the process is terminated
    by an orchestrator or job scheduler.
    """
    signal.signal(signal.SIGTERM, _sigterm_handler)


_SDK_SYMBOLS = {
    "OTelFixture": ("bsb_otel.testing", "OTelFixture"),
    "JSONLinesSpanExporter": ("bsb_otel.exporters", "JSONLinesSpanExporter"),
}


def __getattr__(name):
    if name in _SDK_SYMBOLS:
        module_path, attr = _SDK_SYMBOLS[name]
        import importlib

        return getattr(importlib.import_module(module_path), attr)
    raise AttributeError(f"module 'bsb_otel' has no attribute {name!r}")


__all__ = [
    "BsbTracer",
    "JSONLinesSpanExporter",
    "OTelFixture",
    "TerminationError",
    "ensure_spans_on_exit",
    "get_bsb_tracer",
]
