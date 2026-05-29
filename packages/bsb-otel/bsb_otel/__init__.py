"""
BSB OpenTelemetry integration package.

Entry-point DMZ. This module is loaded eagerly by ``opentelemetry-instrument``
whenever it discovers any of ``bsb_otel``'s entry points (env vars,
exporters, distro). Keeping this file empty — no module-level imports beyond
the standard library — guarantees the DMZ rule: nothing here can drag in
``bsb``, which would fire ``MPI_Init`` prematurely.

Under ``opentelemetry-instrument``'s two-phase startup (entry-point
discovery before ``execl``, then sitecustomize after), a too-early
``MPI_Init`` runs twice and exhausts the SLURM PMI slot — the second
init fails with PMI2 error 14.

The DMZ rule: no top-level ``bsb*`` import in this file or any module
reachable from a registered entry point (``bsb_otel._otel_env``,
``bsb_otel.exporters``, ``bsb_otel._distro``). Transitive imports through
``bsb`` are unpredictable — ``bsb.services`` may get pulled in by something
seemingly innocent — so the rule forbids ``bsb`` entirely, not just
``bsb.services``.

Public API: import directly from the submodule that owns each symbol::

    from bsb_otel.tracer import BsbTracer, get_bsb_tracer
    from bsb_otel.tracer import local_tracing, use_communicator
    from bsb_otel.tracer import TerminationError, ensure_spans_on_exit
    from bsb_otel.exporters import JSONLinesSpanExporter
    from bsb_otel.replay import replay_files
    from bsb_otel.testing import OTelFixture
"""
