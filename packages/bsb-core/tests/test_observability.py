import abc
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from bsb import MPI, handle_command
from bsb.profiling import _instrument_node
from bsb_otel.testing import OTelFixture
from bsb_otel.tracer import get_bsb_tracer

_tracer = get_bsb_tracer("bsb-core")
from bsb_test.parallel import skip_parallel, skip_serial  # noqa: E402

# ---------------------------------------------------------------------------
# Minimal ABC + concrete pair used by TestTelemetryInterfaces.
# _instrument_node is called once at class-definition time, mirroring what
# @config.node does via config/_attrs.py:83.
# ---------------------------------------------------------------------------


class _AbstractBase(abc.ABC):
    @abc.abstractmethod
    def compute(self) -> int: ...


class _ConcreteImpl(_AbstractBase):
    def compute(self) -> int:
        return 42

    def __tree__(self):
        return {}


_instrument_node(_ConcreteImpl)


# ---------------------------------------------------------------------------
# Subprocess helper for exit-condition tests
# ---------------------------------------------------------------------------

# opentelemetry-instrument lives next to the current Python executable.
_OTEL_INSTRUMENT = str(Path(sys.executable).parent / "opentelemetry-instrument")


def _run_trace_subprocess(code, *, timeout=10):
    """
    Run *code* via ``opentelemetry-instrument python -c <code>`` with the
    JSONLines exporter writing to a temp file.  Returns the list of captured
    span dicts.

    ``ensure_spans_on_exit()`` is NOT called automatically; include it in
    *code* if the test requires SIGTERM handling.
    """
    with tempfile.NamedTemporaryFile(suffix=".jsonlines", delete=False) as tf:
        span_file = tf.name

    # Strip MPI launcher env vars so the spawned child does not try to attach
    # to the parent rank's MPI runtime. Without this, an os._exit(1) inside a
    # subprocess of an MPI rank can cause OpenMPI to abort the whole job.
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("OMPI_", "PMI_", "PMIX_", "PMI2_", "SLURM_"))
        and k != "MPI_LOCALRANKID"
    }
    env.update(
        {
            "OTEL_TRACES_EXPORTER": "jsonlines",
            "OTEL_EXPORTER_JSONLINES_PATH": span_file,
        }
    )

    try:
        proc = subprocess.Popen(
            [_OTEL_INSTRUMENT, sys.executable, "-c", code],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        spans = []
        with contextlib.suppress(FileNotFoundError), open(span_file) as f:
            for line in f:
                line = line.strip()
                if line:
                    spans.append(json.loads(line))

        return spans
    finally:
        with contextlib.suppress(OSError):
            os.unlink(span_file)


# ===========================================================================
# Tests
# ===========================================================================


class TestTelemetryCliCommand(unittest.TestCase):
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

        spans = results()
        if MPI.get_rank() == 0:
            # Root rank records the real broadcast span.
            self.assertEqual(len(spans), 1, "Expected only CLI span on root rank")
            self.assertEqual(spans[0]["name"], "cli")
            self.assertEqual(spans[0]["kind"], "SpanKind.INTERNAL")
            self.assertEqual(spans[0]["attributes"]["bsb.cli_command"], ["--version"])
            self.assertEqual(spans[0]["attributes"]["mpi.rank"], 0)
        else:
            # Non-root ranks receive a NonRecordingSpan and record nothing.
            self.assertEqual(len(spans), 0, "Non-root ranks should not record CLI span")


class TestTelemetryInterfaces(unittest.TestCase):
    def test_component_method_traced(self):
        """
        Abstract methods implemented in a concrete class decorated with
        @config.node (or instrumented via _instrument_node directly) are
        automatically wrapped in an OTel span.
        """
        with OTelFixture() as results:
            _ConcreteImpl().compute()

        spans = results()
        self.assertEqual(len(spans), 1, "Expected exactly one component-method span")
        span = spans[0]
        self.assertEqual(span["name"], "_ConcreteImpl.compute")
        attrs = span["attributes"]
        self.assertEqual(attrs["bsb.type"], "component_method")
        self.assertEqual(attrs["bsb.component_type"], "_AbstractBase")
        self.assertEqual(attrs["bsb.component_class"], "_ConcreteImpl")
        self.assertEqual(attrs["bsb.component_method"], "compute")
        self.assertEqual(attrs["mpi.rank"], MPI.get_rank())


class TestTelemetryMPI(unittest.TestCase):
    @skip_serial
    def test_mpi_rank_size_attributes(self):
        """
        Every span carries the correct mpi.rank and mpi.size for the rank it
        was recorded on.
        """
        with OTelFixture() as results, _tracer.trace("probe"):
            pass

        my_spans = results()
        all_spans = MPI.allgather(my_spans)  # list[list[dict]], one per rank

        for rank, rank_spans in enumerate(all_spans):
            self.assertEqual(len(rank_spans), 1, f"Rank {rank}: expected 1 span")
            attrs = rank_spans[0]["attributes"]
            self.assertEqual(
                attrs["mpi.rank"],
                rank,
                f"Rank {rank}: mpi.rank attribute is wrong",
            )
            self.assertEqual(
                attrs["mpi.size"],
                MPI.get_size(),
                f"Rank {rank}: mpi.size attribute is wrong",
            )

    @skip_serial
    def test_mpi_broadcast_parent_chain(self):
        """
        Under a broadcast root span, every rank's spans must:
        * share the same trace_id as the broadcast root
        * have rank_child parented directly to the broadcast root span
        * have rank_grandchild parented to the same rank's rank_child span
          (not to rank 0's copy)

        This verifies the full "back all the way up to the single broadcasted
        root" property.
        """
        with (
            OTelFixture() as results,
            _tracer.trace("broadcast_root"),
            _tracer.trace("rank_child"),
            _tracer.trace("rank_grandchild"),
        ):
            pass

        my_spans = results()
        all_spans = MPI.allgather(my_spans)

        # Rank 0 records broadcast_root + rank_child + rank_grandchild.
        # Other ranks record only rank_child + rank_grandchild (broadcast_root
        # is a NonRecordingSpan on those ranks).
        root_span = next(s for s in all_spans[0] if s["name"] == "broadcast_root")
        root_trace_id = root_span["context"]["trace_id"]
        root_span_id = root_span["context"]["span_id"]

        for rank, rank_spans in enumerate(all_spans):
            child = next(s for s in rank_spans if s["name"] == "rank_child")
            grandchild = next(s for s in rank_spans if s["name"] == "rank_grandchild")

            # All spans share the same trace.
            self.assertEqual(
                child["context"]["trace_id"],
                root_trace_id,
                f"Rank {rank} rank_child has wrong trace_id",
            )
            self.assertEqual(
                grandchild["context"]["trace_id"],
                root_trace_id,
                f"Rank {rank} rank_grandchild has wrong trace_id",
            )

            # rank_child on every rank is parented to the broadcast root.
            self.assertEqual(
                child["parent_id"],
                root_span_id,
                f"Rank {rank} rank_child should be parented to broadcast root",
            )

            # rank_grandchild is parented to the same rank's rank_child.
            self.assertEqual(
                grandchild["parent_id"],
                child["context"]["span_id"],
                f"Rank {rank} rank_grandchild should be parented to its own rank_child",
            )


@skip_parallel
class TestTelemetryExitConditions(unittest.TestCase):
    """
    Exit-condition tests run the code under opentelemetry-instrument so that
    the OTel SDK is fully configured (BatchSpanProcessor + atexit shutdown),
    matching real production behaviour.
    """

    def test_sys_exit_during_span(self):
        """sys.exit() inside a span must not swallow the span."""
        spans = _run_trace_subprocess(
            "from bsb_otel.tracer import get_bsb_tracer\n"
            "import sys\n"
            "with get_bsb_tracer('bsb-core').trace('work'): sys.exit(0)\n"
        )
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["name"], "work")

    def test_exception_during_span(self):
        """
        An unhandled exception propagating out of a span still ends the span
        (with ERROR status).
        """
        spans = _run_trace_subprocess(
            "from bsb_otel.tracer import get_bsb_tracer\n"
            "with get_bsb_tracer('bsb-core').trace('work'): raise ValueError('boom')\n"
        )
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["name"], "work")
        self.assertEqual(spans[0]["status"]["status_code"], "ERROR")

    def test_sigterm_during_span(self):
        """
        SIGTERM received while inside a span raises TerminationError (installed
        by ensure_spans_on_exit()), which unwinds the stack cleanly so the span
        is ended and collected before the process exits.
        """
        spans = _run_trace_subprocess(
            "import signal\n"
            "from bsb_otel.tracer import ensure_spans_on_exit\n"
            "ensure_spans_on_exit()\n"
            "from bsb_otel.tracer import get_bsb_tracer\n"
            "with get_bsb_tracer('bsb-core').trace('work'):\n"
            "    signal.raise_signal(signal.SIGTERM)\n"
        )
        self.assertEqual(len(spans), 1)
        self.assertEqual(spans[0]["name"], "work")

    @skip_parallel
    @unittest.expectedFailure
    def test_hard_exit_loses_span(self):
        """
        os._exit() bypasses all Python cleanup (no __exit__, no atexit).
        This documents the known limitation: spans cannot be collected when
        the process is forcibly torn down (e.g. real MPI abort or SIGKILL).
        """
        spans = _run_trace_subprocess(
            "import os\n"
            "from bsb_otel.tracer import get_bsb_tracer\n"
            "with get_bsb_tracer('bsb-core').trace('work'): os._exit(1)\n"
        )
        self.assertEqual(len(spans), 1, "Hard exit should not collect spans")
