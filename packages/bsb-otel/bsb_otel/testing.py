import json
import os
import tempfile
import typing
import unittest
from collections import deque

from bsb.profiling import _telemetry_trace
from opentelemetry import trace


def _pop(queue):
    try:
        return queue.pop()
    except IndexError:
        return None


def _visit_test_cases(root, visitor):
    queue = deque([root])
    while node := _pop(queue):
        if isinstance(node, unittest.TestCase):
            visitor(node)
        else:
            queue.extend(reversed(list(node)))


def _wrap_case(case: unittest.TestCase):
    original_run = case.run

    def wrapped_run(*args, **kwargs):
        with _telemetry_trace(
            case.id(),
            attributes={
                "python.test_package": case.id().split(".")[0],
                "python.test_module": case.id().split(".")[1],
                "python.test_class": case.id().split(".")[2],
                "python.test_case": case.id().split(".")[3],
            },
            broadcast=True,
        ):
            return original_run(*args, **kwargs)

    case.run = wrapped_run


def wrap_tests_with_traces(suite):
    """
    Wrap every :class:`unittest.TestCase` in *suite* so that each test run is
    recorded as an OpenTelemetry trace span.

    Intended to be called from a ``load_tests`` hook::

        from bsb_otel.testing import wrap_tests_with_traces

        def load_tests(loader, tests, pattern):
            suite = loader.discover("tests")
            wrap_tests_with_traces(suite)
            return suite
    """
    _visit_test_cases(suite, _wrap_case)


def _get_file_tracer_provider(file: typing.IO, buffered=True):
    """
    Create a provider that exports traces to a file as JSON lines.
    """
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    exporter = ConsoleSpanExporter(
        out=file, formatter=lambda span: span.to_json(indent=None) + os.linesep
    )
    processor = (BatchSpanProcessor if buffered else SimpleSpanProcessor)(exporter)
    provider = TracerProvider()
    provider.add_span_processor(processor)

    return provider


class OTelFixture:
    """
    Context manager that overrides the global tracer provider with a custom one
    that exports to a temporary file, allowing tests to assert on recorded spans.

    The global tracer provider is restored on exit.

    Usage::

        with OTelFixture() as results:
            handle_command(["--version"])

        spans = results()
        assert spans[0]["name"] == "cli"
    """

    def __enter__(self):
        self._old_provider = trace.get_tracer_provider()
        self.temp_file = tempfile.NamedTemporaryFile("w+")
        provider = _get_file_tracer_provider(file=self.temp_file)
        # Note: overriding _TRACER_PROVIDER is not officially supported by OTel
        trace._TRACER_PROVIDER = provider

        def reader():
            if not hasattr(self, "results"):
                raise RuntimeError("Reader called before end of context")
            return self.results

        return reader

    def __exit__(self, exc_type, exc_val, exc_tb):
        provider = trace.get_tracer_provider()
        provider.shutdown()
        trace._TRACER_PROVIDER = self._old_provider
        self.temp_file.seek(0)
        self.results = [json.loads(line) for line in self.temp_file.readlines()]
        self.temp_file.close()


__all__ = ["OTelFixture", "wrap_tests_with_traces"]
