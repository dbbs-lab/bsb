import os
import tempfile
import time
import unittest

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from bsb_otel._otel_env import OTEL_EXPORTER_JSONLINES_PATH
from bsb_otel.exporters import JSONLinesSpanExporter
from bsb_otel.replay import _iso_to_ns, load_spans, replay_spans

# A span recorded years ago, well outside any default collector lookback window.
_OLD_SPAN = {
    "name": "old",
    "context": {"trace_id": "0x" + "1" * 32, "span_id": "0x" + "2" * 16},
    "kind": "SpanKind.INTERNAL",
    "parent_id": None,
    "start_time": "2020-01-01T00:00:00.000000Z",
    "end_time": "2020-01-01T00:00:05.000000Z",
    "status": {"status_code": "UNSET"},
    "attributes": {},
    "events": [],
}


def _memory_provider():
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


def _record_to_jsonlines(path):
    """Record a parent span with one child to ``path`` via the jsonlines exporter."""
    os.environ[OTEL_EXPORTER_JSONLINES_PATH] = path
    try:
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(JSONLinesSpanExporter()))
        tracer = provider.get_tracer("test-replay")
        with (
            tracer.start_as_current_span("parent", attributes={"k": "v"}),
            tracer.start_as_current_span("child"),
        ):
            pass
        provider.shutdown()
    finally:
        del os.environ[OTEL_EXPORTER_JSONLINES_PATH]


class TestReplayRoundTrip(unittest.TestCase):
    def test_roundtrip_preserves_identity_and_hierarchy(self):
        with tempfile.TemporaryDirectory() as d:
            jsonlines = os.path.join(d, "traces.jsonlines")
            _record_to_jsonlines(jsonlines)

            recorded = load_spans([jsonlines])
            self.assertEqual({s["name"] for s in recorded}, {"parent", "child"})

            exporter = InMemorySpanExporter()
            provider = TracerProvider()
            provider.add_span_processor(SimpleSpanProcessor(exporter))
            n = replay_spans(recorded, provider=provider)
            self.assertEqual(n, 2)

            replayed = {s.name: s for s in exporter.get_finished_spans()}
            self.assertEqual(set(replayed), {"parent", "child"})

            # ids survive the round-trip
            by_name = {s["name"]: s for s in recorded}
            for name in ("parent", "child"):
                ctx = replayed[name].get_span_context()
                want = by_name[name]["context"]
                self.assertEqual(f"0x{ctx.trace_id:032x}", want["trace_id"])
                self.assertEqual(f"0x{ctx.span_id:016x}", want["span_id"])

            # child keeps parent's span id, so the trace tree is intact
            self.assertEqual(
                replayed["child"].parent.span_id,
                replayed["parent"].get_span_context().span_id,
            )
            self.assertIsNone(replayed["parent"].parent)
            self.assertEqual(replayed["parent"].attributes["k"], "v")

    def test_replay_without_sdk_provider_raises(self):
        # A bare (no-op) provider has no _active_span_processor to replay into.
        with self.assertRaises(RuntimeError):
            replay_spans([], provider=object())


class TestReplayTimestampShift(unittest.TestCase):
    def test_shift_to_now_anchors_end_to_replay_time_and_keeps_duration(self):
        provider, exporter = _memory_provider()
        now = time.time_ns()
        replay_spans([dict(_OLD_SPAN)], provider=provider, shift_to_now=True)
        span = exporter.get_finished_spans()[0]

        original_duration = _iso_to_ns(_OLD_SPAN["end_time"]) - _iso_to_ns(
            _OLD_SPAN["start_time"]
        )
        # Duration is preserved exactly; the span now ends around replay time.
        self.assertEqual(span.end_time - span.start_time, original_duration)
        self.assertAlmostEqual(span.end_time, now, delta=5_000_000_000)

    def test_keep_timestamps_leaves_original_times(self):
        provider, exporter = _memory_provider()
        replay_spans([dict(_OLD_SPAN)], provider=provider, shift_to_now=False)
        span = exporter.get_finished_spans()[0]
        self.assertEqual(span.start_time, _iso_to_ns(_OLD_SPAN["start_time"]))
        self.assertEqual(span.end_time, _iso_to_ns(_OLD_SPAN["end_time"]))


if __name__ == "__main__":
    unittest.main()
