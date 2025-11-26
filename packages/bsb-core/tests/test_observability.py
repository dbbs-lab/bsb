import contextlib
import json
import os
import tempfile
import unittest

from bsb import MPI, handle_command
from bsb.profiling import _get_file_tracer_provider
from opentelemetry import trace


class OTelFixture:
    """
    This fixture overrides the global tracer provider with a custom one that exports to a file.
    The global tracer provider is restored afterward.
    """

    def __enter__(self):
        # Save old provider
        self._old_provider = trace.get_tracer_provider()
        # Create a new provider that exports to file
        # for the tests to run assertions on
        self.temp_file = tempfile.NamedTemporaryFile("w+")
        # Override the global tracer, note: this is not supported by OTel
        provider = _get_file_tracer_provider(file=self.temp_file)
        trace._TRACER_PROVIDER = provider

        def reader():
            if not hasattr(self, "results"):
                raise RuntimeError("Reader called before end of context")
            return self.results

        return reader

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Flush spans and restore global provider
        provider = trace.get_tracer_provider()
        provider.shutdown()
        trace._TRACER_PROVIDER = self._old_provider
        self.temp_file.seek(0)
        self.results = [json.loads(line) for line in self.temp_file.readlines()]
        self.temp_file.close()


class TestTelemetry(unittest.TestCase):
    def test_same_process_cli_command(self):
        """
        Tests whether traces are collected for a normal CLI command.
        """
        with (
            # Silence output of --version to stdout
            open(os.devnull, "w") as devnull,
            contextlib.redirect_stdout(devnull),
            # Capture otel output
            OTelFixture() as results,
        ):
            handle_command(["--version"])

        # Assert that span was recorded
        spans = results()
        self.assertEqual(len(spans), 1, "Expected only CLI span")
        self.assertEqual(spans[0]["name"], "cli")
        self.assertEqual(spans[0]["kind"], "SpanKind.INTERNAL")
        self.assertEqual(spans[0]["attributes"]["bsb.cli_command"], ["--version"])
        self.assertEqual(spans[0]["attributes"]["mpi.rank"], MPI.get_rank())
