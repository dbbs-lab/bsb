import contextlib
import os
import unittest

from bsb import MPI, handle_command
from bsb_otel.testing import OTelFixture


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
