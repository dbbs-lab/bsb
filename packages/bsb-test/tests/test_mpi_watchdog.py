import contextlib
import inspect
import io
import os
import shutil
import subprocess
import sys
import textwrap
import unittest
from unittest import mock

from bsb_test import mpi_watchdog, skip_parallel


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


def _case(test):
    """
    Make a test case that runs ``test``, built here so that discovery skips it.
    """
    return type("Case", (unittest.TestCase,), {"test_a": test})("test_a")


class TestPatchedResult(unittest.TestCase):
    """
    Run test cases into a result class wrapped by the watchdog, with MPI and
    faulthandler mocked, so that no rank is aborted and no timer is left running.
    """

    def setUp(self):
        # Under MPI the watchdog already wraps `unittest.TestResult`: start from its
        # unwrapped methods so that it is applied only once.
        names = ("startTest", "stopTest", "addError", "addFailure", "addSubTest")
        Result = type(
            "Result",
            (unittest.TestResult,),
            {n: inspect.unwrap(getattr(unittest.TestResult, n)) for n in names},
        )
        mpi_watchdog._patch(Result, 5)
        self.result = Result()
        patches = [
            mock.patch.object(mpi_watchdog, "MPI"),
            mock.patch.object(mpi_watchdog, "_faulthandler"),
        ]
        self.mpi, self.faulthandler = (p.start() for p in patches)
        for p in patches:
            self.addCleanup(p.stop)
        self.mpi.get_rank.return_value = 1
        self.stderr = io.StringIO()

    def run_case(self, test):
        with contextlib.redirect_stderr(self.stderr):
            _case(test).run(self.result)

    def assertAborted(self, message):
        self.mpi.abort.assert_called_once_with(1)
        stderr = self.stderr.getvalue()
        self.assertIn("test_a", stderr, "header should name the test")
        self.assertIn("FAILED ON RANK 1 (ABORTING ALL RANKS)", stderr)
        self.assertIn(message, stderr, "traceback of the failure should be printed")

    def test_failure_aborts(self):
        self.run_case(lambda case: case.fail("it failed"))
        self.assertAborted("it failed")
        self.assertEqual(1, len(self.result.failures), "failure should be recorded")

    def test_error_aborts(self):
        def test(case):
            raise ValueError("it broke")

        self.run_case(test)
        self.assertAborted("it broke")
        self.assertEqual(1, len(self.result.errors), "error should be recorded")

    def test_subtest_failure_aborts(self):
        def test(case):
            with case.subTest(i=0):
                pass
            with case.subTest(i=1):
                case.fail("subtest failed")

        self.run_case(test)
        self.assertAborted("subtest failed")
        self.assertIn("i=1", self.stderr.getvalue(), "header should name the subtest")
        self.assertEqual(1, len(self.result.failures), "failure should be recorded")

    def test_pass_does_not_abort(self):
        def test(case):
            with case.subTest(i=0):
                pass

        self.run_case(test)
        self.run_case(lambda case: case.skipTest("skipped"))
        self.run_case(unittest.expectedFailure(lambda case: case.fail("expected")))
        self.mpi.abort.assert_not_called()
        self.assertEqual("", self.stderr.getvalue())
        self.assertEqual(3, self.result.testsRun)
        self.assertEqual(1, len(self.result.skipped))
        self.assertEqual(1, len(self.result.expectedFailures))

    def test_timer_per_test(self):
        self.run_case(lambda case: None)
        self.run_case(lambda case: None)
        self.assertEqual(
            [mock.call(5, exit=True)] * 2,
            self.faulthandler.dump_traceback_later.call_args_list,
            "each test should start its own timer",
        )
        self.assertEqual(2, self.faulthandler.cancel_dump_traceback_later.call_count)


class TestInstall(unittest.TestCase):
    def setUp(self):
        patches = [
            mock.patch.object(mpi_watchdog, "_installed", False),
            mock.patch.object(mpi_watchdog, "_patch"),
            mock.patch.object(mpi_watchdog, "MPI"),
            mock.patch.dict(os.environ),
        ]
        _, self.patch, self.mpi, _ = (p.start() for p in patches)
        for p in patches:
            self.addCleanup(p.stop)
        self.mpi.get_size.return_value = 2
        os.environ.pop("BSB_TEST_NO_WATCHDOG", None)
        os.environ.pop("BSB_TEST_TIMEOUT", None)

    def test_install(self):
        mpi_watchdog.install()
        self.patch.assert_called_once_with(unittest.TestResult, 600)
        self.assertTrue(mpi_watchdog._installed)
        mpi_watchdog.install()
        self.patch.assert_called_once()

    def test_timeout(self):
        os.environ["BSB_TEST_TIMEOUT"] = "7.5"
        mpi_watchdog.install()
        self.patch.assert_called_once_with(unittest.TestResult, 7.5)

    def test_timeout_argument(self):
        os.environ["BSB_TEST_TIMEOUT"] = "7.5"
        mpi_watchdog.install(3)
        self.patch.assert_called_once_with(unittest.TestResult, 3)

    def test_serial(self):
        self.mpi.get_size.return_value = 1
        mpi_watchdog.install()
        self.patch.assert_not_called()
        self.assertFalse(mpi_watchdog._installed)

    def test_disabled(self):
        os.environ["BSB_TEST_NO_WATCHDOG"] = "1"
        mpi_watchdog.install()
        self.patch.assert_not_called()
