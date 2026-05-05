import unittest

from bsb_otel import BsbTracer, _tracer_registry, get_bsb_tracer


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
    def test_trace_yields_a_span(self):
        # Without an SDK provider configured, OTel returns a NonRecordingSpan;
        # the tracer should still produce a usable context manager.
        with get_bsb_tracer("bsb-otel").trace("probe") as span:
            self.assertIsNotNone(span)
