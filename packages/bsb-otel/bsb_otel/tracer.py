"""
Tracer and lifecycle helpers for the BSB OpenTelemetry integration.

This module is outside the entry-point DMZ — it imports ``bsb.services`` at
module top, which fires ``MPI_Init`` at import time. Import its members
via deep imports (``from bsb_otel.tracer import ...``) so the heavy
bsb/MPI dependency only loads when user code actually needs the tracer.
Do not register anything from this module as a Python entry point, and
do not import it from ``bsb_otel/__init__.py`` at module top level.
"""

from __future__ import annotations

import contextlib
import contextvars
import importlib.metadata
import signal

from bsb.services import MPI
from opentelemetry import trace
from opentelemetry.trace import NonRecordingSpan, get_current_span

# Per-context override for the MPI communicator BsbTracer uses to broadcast
# parent span contexts. The default (``None``) means "use the global
# ``bsb.services.MPI`` communicator" (typically ``MPI.COMM_WORLD``). This
# affects ONLY tracing's internal broadcast — it is not a general MPI scope
# override; other BSB code keeps using the global ``MPI`` service.
_trace_comm: contextvars.ContextVar = contextvars.ContextVar(
    "bsb_otel_trace_communicator", default=None
)


@contextlib.contextmanager
def use_communicator(comm):
    """
    Override the MPI communicator that :class:`BsbTracer` uses for span
    broadcasts within this block.

    - Pass ``mpi4py.MPI.COMM_SELF`` (size 1 from this rank's view) to
      disable cross-rank correlation — each rank traces independently.
      Use :func:`local_tracing` for that case.
    - Pass any sub-communicator to broadcast within that group only.
    - The default is the global ``bsb.services.MPI`` communicator.

    .. note::
       This only affects the bsb-otel broadcast logic. ``mpi.rank`` and
       ``mpi.size`` span attributes still report the *global* rank/size
       from ``bsb.services.MPI``. Other BSB code (locks, gather, etc.)
       is unaffected.

    Implemented as a :class:`contextvars.ContextVar`, so it propagates
    across asyncio tasks and through ``contextvars.copy_context().run(...)``
    (which the BSB job pool uses), but does not leak across threads
    spawned with the bare ``threading.Thread``.
    """
    token = _trace_comm.set(comm)
    try:
        yield
    finally:
        _trace_comm.reset(token)


@contextlib.contextmanager
def local_tracing():
    """
    Disable cross-rank broadcast for spans created inside this block.

    Shorthand for ``use_communicator(mpi4py.MPI.COMM_SELF)``. Use this
    around rank-divergent code paths (where different ranks make different
    sequences of ``trace()`` calls) to avoid the collective-broadcast
    deadlock that would otherwise occur.

    Inside the block each rank only synchronises with the chosen
    communicator (``COMM_SELF`` — i.e. itself), so no new cross-rank
    broadcast root is created. A cross-rank parent established *before*
    the block is preserved: spans created inside still inherit it as
    their parent, so their trace_id stays correlated across ranks.

    Falls back to a no-op if mpi4py is not importable, since the broadcast
    machinery is then already inactive.
    """
    try:
        from mpi4py.MPI import COMM_SELF
    except ImportError:
        yield
        return
    with use_communicator(COMM_SELF):
        yield


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


_tracer_registry: dict[str, BsbTracer] = {}


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

        # mpi.rank/mpi.size always reflect the GLOBAL communicator so spans
        # are comparable across runs regardless of the contextual broadcast
        # comm chosen via ``use_communicator``.
        attributes["mpi.rank"] = MPI.get_rank()
        attributes["mpi.size"] = MPI.get_size()

        # Pick the communicator BsbTracer broadcasts on. Defaults to the
        # global MPI service; ``use_communicator``/``local_tracing`` can
        # override it per scope.
        comm = _trace_comm.get()
        if comm is None:
            rank, size = MPI.get_rank(), MPI.get_size()

            def bcast(obj, root=0):
                return MPI.bcast(obj, root=root)
        else:
            rank, size = comm.Get_rank(), comm.Get_size()

            def bcast(obj, root=0):
                return comm.bcast(obj, root=root)

        _btrace(f"trace[{name!r}] enter bcast_rank={rank}/{size}")

        # In serial mode the broadcast dance is dead weight: bcast is a no-op
        # and the rank>0 branch is unreachable. Just create a normal span.
        # This is also the path taken when ``local_tracing()`` is active,
        # since COMM_SELF reports size 1.
        if size == 1:
            _btrace(f"trace[{name!r}] serial fast-path")
            return self._otel_tracer.start_as_current_span(name, attributes=attributes)

        # No SDK provider configured: nothing meaningful to broadcast, and
        # imposing a collective barrier on every trace() call would deadlock
        # any rank-divergent caller. Stay true to OTel's "API works without
        # SDK" contract — each rank traces locally as a no-op.
        if trace._TRACER_PROVIDER is None:
            _btrace(f"trace[{name!r}] no SDK provider, local-only")
            return self._otel_tracer.start_as_current_span(name, attributes=attributes)

        if not get_current_span().get_span_context().is_valid:
            _btrace(f"trace[{name!r}] no parent → broadcast branch")
            if rank == 0:
                parent_span_ctx_mgr = self._otel_tracer.start_as_current_span(
                    name, attributes=attributes
                )
                parent_span = parent_span_ctx_mgr.__enter__()
                parent_span_context = parent_span.get_span_context()
                # Broadcast the parent context so non-root ranks can attach
                # it. If the local tracer is a no-op (no SDK provider) the
                # context is invalid and there's nothing meaningful to share;
                # broadcast None instead so non-root ranks also fall through
                # to a local no-op span.
                _btrace(
                    f"trace[{name!r}] rank0 pre-bcast "
                    f"valid={parent_span_context.is_valid}"
                )
                bcast(
                    parent_span_context if parent_span_context.is_valid else None,
                    root=0,
                )
                _btrace(f"trace[{name!r}] rank0 post-bcast")
                return _SpanContextManagerProxy(parent_span_ctx_mgr, parent_span)
            else:
                _btrace(f"trace[{name!r}] rank{rank} pre-bcast (waiting on root)")
                parent_span_context = bcast(None, root=0)
                _btrace(
                    f"trace[{name!r}] rank{rank} post-bcast got={parent_span_context!r}"
                )
                if parent_span_context is None:
                    return self._otel_tracer.start_as_current_span(
                        name, attributes=attributes
                    )
                return trace.use_span(
                    NonRecordingSpan(parent_span_context), end_on_exit=False
                )

        _btrace(f"trace[{name!r}] inherit parent → child span")
        return self._otel_tracer.start_as_current_span(name, attributes=attributes)


def _btrace(msg):
    """Diagnostic trace to stderr; gated on $BSB_OTEL_TRACE."""
    import os
    import sys
    import time

    if not os.environ.get("BSB_OTEL_TRACE"):
        return
    rank = os.environ.get("OMPI_COMM_WORLD_RANK", "?")
    print(
        f"[bsb_otel t={time.monotonic():.3f}s rank={rank}] {msg}",
        file=sys.stderr,
        flush=True,
    )


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
