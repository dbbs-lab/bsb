import json
import os
import tempfile
import typing

from opentelemetry import trace


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


__all__ = ["OTelFixture"]
