import os
import shutil
import subprocess
import sys
import textwrap
import unittest

from bsb_test import skip_parallel


def _run_mpi(body, **env):
    """
    Run a unittest module made of ``body`` on 2 ranks, with ``bsb_test`` imported.
    """
    script = "import unittest\nfrom bsb_test import MPI\n" + textwrap.dedent(body)
    script += "\nunittest.main()\n"
    # Only spawned from a serial test, but strip any MPI launcher state anyway.
    child_env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("OMPI_", "PMI_", "PMIX_", "PMI2_", "PRTE_"))
    }
    child_env.pop("BSB_TEST_NO_WATCHDOG", None)
    # Python 3.14+ colours the unittest report when asked to, as Nx does through
    # `FORCE_COLOR`. Keep the output plain so that it can be matched.
    child_env.pop("FORCE_COLOR", None)
    child_env["PYTHON_COLORS"] = "0"
    child_env["NO_COLOR"] = "1"
    child_env.update(env)
    return subprocess.run(
        ["mpiexec", "-n", "2", sys.executable, "-c", script],
        capture_output=True,
        text=True,
        timeout=120,
        env=child_env,
    )


@skip_parallel
@unittest.skipIf(shutil.which("mpiexec") is None, "mpiexec required.")
class TestMPIWatchdog(unittest.TestCase):
    def test_one_rank_fails(self):
        # Rank 1 fails before a barrier that rank 0 waits in: without the watchdog the
        # run hangs until the subprocess timeout.
        proc = _run_mpi(
            """
            class Case(unittest.TestCase):
                def test_a(self):
                    self.assertNotEqual(1, MPI.get_rank(), "rank 1 failed")
                    MPI.barrier()
            """
        )
        self.assertNotEqual(0, proc.returncode, "run should fail")
        self.assertIn("FAILED ON RANK 1 (ABORTING ALL RANKS)", proc.stderr)
        self.assertIn("rank 1 failed", proc.stderr)

    def test_one_rank_errors_in_setup(self):
        proc = _run_mpi(
            """
            class Case(unittest.TestCase):
                def setUp(self):
                    if MPI.get_rank() == 1:
                        raise ValueError("setup broke")

                def test_a(self):
                    MPI.barrier()
            """
        )
        self.assertNotEqual(0, proc.returncode, "run should fail")
        self.assertIn("FAILED ON RANK 1 (ABORTING ALL RANKS)", proc.stderr)
        self.assertIn("setup broke", proc.stderr)

    def test_one_rank_fails_subtest(self):
        proc = _run_mpi(
            """
            class Case(unittest.TestCase):
                def test_a(self):
                    with self.subTest(i=0):
                        self.assertNotEqual(1, MPI.get_rank(), "rank 1 failed")
                    MPI.barrier()
                    MPI.barrier()
            """
        )
        self.assertNotEqual(0, proc.returncode, "run should fail")
        self.assertIn("FAILED ON RANK 1 (ABORTING ALL RANKS)", proc.stderr)

    def test_hang_times_out(self):
        # Rank 1 leaves without error, rank 0 waits in the barrier for ever.
        proc = _run_mpi(
            """
            class Case(unittest.TestCase):
                def test_a(self):
                    if MPI.get_rank() == 0:
                        MPI.barrier()
            """,
            BSB_TEST_TIMEOUT="2",
        )
        self.assertNotEqual(0, proc.returncode, "run should fail")
        self.assertIn("Timeout", proc.stderr, "no stack dump of the hung rank")
        self.assertIn("test_a", proc.stderr, "stack dump should show the hung test")

    def test_passing_run(self):
        # Each test stays under the timeout, though the run as a whole does not: the
        # timeout must be reset for each test. Skips must not abort the run.
        proc = _run_mpi(
            """
            import time

            class Case(unittest.TestCase):
                def test_a(self):
                    time.sleep(1.5)
                    MPI.barrier()

                def test_b(self):
                    time.sleep(1.5)
                    MPI.barrier()

                def test_c(self):
                    self.skipTest("skipped")

                @unittest.expectedFailure
                def test_d(self):
                    self.fail("expected")
            """,
            BSB_TEST_TIMEOUT="2",
        )
        self.assertEqual(0, proc.returncode, proc.stderr)
        self.assertNotIn("ABORTING", proc.stderr)

    def test_disabled(self):
        # Both ranks fail, so nothing hangs: unittest reports the failure itself.
        proc = _run_mpi(
            """
            class Case(unittest.TestCase):
                def test_a(self):
                    self.fail("both ranks fail")
            """,
            BSB_TEST_NO_WATCHDOG="1",
        )
        self.assertNotEqual(0, proc.returncode, "run should fail")
        self.assertNotIn("ABORTING", proc.stderr)
        self.assertIn("FAILED (failures=1)", proc.stderr)


class TestInstallSerial(unittest.TestCase):
    @skip_parallel
    def test_noop_in_serial(self):
        self.assertEqual(
            unittest.TestResult.addFailure.__module__,
            "unittest.result",
            "watchdog should not patch unittest in a serial run",
        )
