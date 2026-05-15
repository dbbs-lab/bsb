import unittest

from opentelemetry import trace as ot

from bsb_otel.testing import OTelFixture
from bsb_otel.tracer import BsbTracer, _tracer_registry, get_bsb_tracer


class TestBsbTracerRegistry(unittest.TestCase):
    def test_get_bsb_tracer_returns_bsb_tracer(self):
        self.assertIsInstance(get_bsb_tracer("bsb-otel"), BsbTracer)

    def test_get_bsb_tracer_is_idempotent(self):
        self.assertIs(get_bsb_tracer("bsb-otel"), get_bsb_tracer("bsb-otel"))

    def test_explicit_version_skips_metadata_lookup(self):
        # Ask for a never-installed package name with an explicit version,
        # so importlib.metadata is not consulted.
        try:
            tracer = get_bsb_tracer("definitely-not-a-real-package", version="0.0.0")
            self.assertIsInstance(tracer, BsbTracer)
        finally:
            _tracer_registry.pop("definitely-not-a-real-package", None)


class TestBsbTracerSpan(unittest.TestCase):
    def test_trace_records_a_span(self):
        with OTelFixture() as results, get_bsb_tracer("bsb-otel").trace("probe"):
            pass
        spans = results()
        # Rank 0 records the broadcast root span; non-root ranks attach a
        # NonRecordingSpan and record nothing.
        from bsb import MPI

        if MPI.get_rank() == 0:
            self.assertEqual([s["name"] for s in spans], ["probe"])
        else:
            self.assertEqual(spans, [])

    def test_trace_no_ops_without_sdk_provider(self):
        # Mirror OTel's "API works without SDK" contract: with no provider
        # configured, BsbTracer.trace must be a usable, non-recording no-op
        # — and the multi-rank broadcast path must not deadlock or raise.
        self.assertIsNone(
            ot._TRACER_PROVIDER,
            "test precondition: no real TracerProvider should be configured",
        )
        with get_bsb_tracer("bsb-otel").trace("noop") as span:
            self.assertFalse(span.is_recording())
