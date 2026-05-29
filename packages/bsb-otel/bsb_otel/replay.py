"""
Replay JSON Lines trace files into the active OpenTelemetry pipeline.

Reads spans written by :class:`~bsb_otel.exporters.JSONLinesSpanExporter`,
reconstructs them as :class:`~opentelemetry.sdk.trace.ReadableSpan` objects and
feeds them to the active tracer provider's span processor. Whatever exporter
``opentelemetry-instrument`` has configured (OTLP to a collector, console, ...)
then receives the replayed traces with their original ids and parent links.

By default the timestamps are shifted forward so the trace ends at the moment of
replay, keeping every span's relative offset and duration intact. This sidesteps
collector search windows (e.g. Jaeger's lookback) that would otherwise hide a
trace recorded long ago. Pass ``shift_to_now=False`` to keep the original times.

This module imports the OpenTelemetry SDK at top level, so it is outside the
entry-point DMZ (see :mod:`bsb_otel`): import it lazily, only from the
``replay-otel`` command handler.
"""

import glob
import json
import time
from datetime import datetime

try:
    from opentelemetry.sdk.trace import Event, InstrumentationScope, ReadableSpan
    from opentelemetry.trace import SpanContext, SpanKind, TraceFlags
    from opentelemetry.trace.status import Status, StatusCode
except ImportError:
    raise ImportError(
        "bsb_otel.replay requires the OpenTelemetry SDK. "
        "Install it with: pip install 'bsb-otel[sdk]'"
    ) from None


def _iso_to_ns(timestamp: str) -> int:
    """Convert an ISO 8601 timestamp (as written by ``to_json``) to epoch ns."""
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    return int(dt.timestamp() * 1e9)


def _make_event(event: dict, delta_ns: int) -> Event:
    return Event(
        event["name"],
        event.get("attributes", {}),
        _iso_to_ns(event["timestamp"]) + delta_ns,
    )


def _make_span(data: dict, resource, delta_ns: int = 0) -> ReadableSpan:
    """
    Reconstruct a single span dict (one JSON Lines record) as a ReadableSpan.

    *delta_ns* is added to the span's and its events' timestamps (0 leaves them
    untouched), shifting the span in time while preserving its duration.
    """
    ctx = data["context"]
    trace_id = int(ctx["trace_id"], 16)

    parent = None
    parent_id = data.get("parent_id")
    if parent_id:
        parent = SpanContext(
            trace_id=trace_id,
            span_id=int(parent_id, 16),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        )

    status = data.get("status") or {}
    status_code = getattr(
        StatusCode, status.get("status_code", "UNSET"), StatusCode.UNSET
    )
    kind = getattr(SpanKind, data["kind"].split(".")[-1], SpanKind.INTERNAL)

    return ReadableSpan(
        name=data["name"],
        context=SpanContext(
            trace_id=trace_id,
            span_id=int(ctx["span_id"], 16),
            is_remote=False,
            trace_flags=TraceFlags(TraceFlags.SAMPLED),
        ),
        parent=parent,
        resource=resource,
        attributes=data.get("attributes", {}),
        events=[_make_event(e, delta_ns) for e in data.get("events", [])],
        kind=kind,
        status=Status(status_code, status.get("description")),
        start_time=_iso_to_ns(data["start_time"]) + delta_ns,
        end_time=_iso_to_ns(data["end_time"]) + delta_ns,
        instrumentation_scope=InstrumentationScope(
            (data.get("instrumentation_scope") or {}).get("name", "bsb_otel")
        ),
    )


def load_spans(paths) -> list:
    """
    Load raw span dicts from one or more JSON Lines files.

    Each path may be a literal file or a glob pattern (e.g. ``traces_*.jsonlines``);
    patterns that match nothing fall through as a literal path so a clear
    ``FileNotFoundError`` is raised.

    :param paths: iterable of file paths or glob patterns
    :returns: list of raw span dicts, in file-and-line order
    """
    raw = []
    for pattern in paths:
        for path in sorted(glob.glob(pattern)) or [pattern]:
            with open(path) as f:
                raw.extend(json.loads(line) for line in f if line.strip())
    return raw


def _shift_delta_ns(spans) -> int:
    """
    Nanoseconds to add to every timestamp so the latest span ends now.

    Anchoring to the latest ``end_time`` shifts the whole batch as one block, so
    every span keeps its relative offset and duration. Returns 0 for an empty
    batch.
    """
    if not spans:
        return 0
    latest = max(_iso_to_ns(s["end_time"]) for s in spans)
    return int(time.time() * 1e9) - latest


def replay_spans(spans, provider=None, shift_to_now=True) -> int:
    """
    Feed reconstructed spans into a tracer provider's active span processor.

    The spans keep their original ids, so the configured exporter forwards them
    as-is. They adopt *provider*'s resource, so the service name shown by the
    collector follows the ``--service_name`` / ``OTEL_RESOURCE_ATTRIBUTES`` of
    the replaying process rather than the recording one.

    :param spans: raw span dicts, e.g. from :func:`load_spans`
    :param provider: tracer provider to replay into; defaults to the active one
    :param shift_to_now: shift all timestamps forward so the latest span ends at
        replay time, keeping relative offsets and durations; set ``False`` to
        keep the original timestamps
    :returns: number of spans replayed
    """
    from opentelemetry import trace

    if provider is None:
        provider = trace.get_tracer_provider()
    processor = getattr(provider, "_active_span_processor", None)
    if processor is None:
        raise RuntimeError(
            "No active OpenTelemetry SDK tracer provider to replay into. Run "
            "under `opentelemetry-instrument` with a configured traces exporter, "
            "e.g. `opentelemetry-instrument --traces_exporter otlp ... bsb "
            "replay-otel <file>`."
        )
    delta_ns = _shift_delta_ns(spans) if shift_to_now else 0
    resource = getattr(provider, "resource", None)
    for span in spans:
        processor.on_end(_make_span(span, resource, delta_ns))
    provider.force_flush()
    return len(spans)


def replay_files(paths, shift_to_now=True) -> int:
    """Load JSON Lines files and replay them into the active tracer provider."""
    from bsb.reporting import report

    paths = list(paths)
    spans = load_spans(paths)
    n = replay_spans(spans, shift_to_now=shift_to_now)
    shifted = " (timestamps shifted to now)" if shift_to_now else ""
    report(f"Replayed {n} spans from {len(paths)} source(s){shifted}.", level=1)
    return n


__all__ = ["load_spans", "replay_spans", "replay_files"]
