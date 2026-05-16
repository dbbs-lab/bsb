# === TEMPORARY: investigate exit-1-without-traceback in `mpiexec -n 2` runs ===
# The parallel bsb-core test pass reports every test `... ok` then dies with
# exit 1 and no Python traceback. To localize the cause, enable two diagnostics:
#   - faulthandler.enable(): dumps the Python stack on fatal signals
#     (SIGSEGV/SIGABRT/SIGBUS/SIGFPE) and C-level aborts (MPI_Abort, h5py).
#   - atexit hook: prints a per-rank marker at normal Python exit. Missing
#     marker for a rank => that rank bypassed Python shutdown (signal/abort/
#     os._exit). Marker WITH an exception => caught a teardown-phase error
#     unittest didn't report.
# Both are no-ops in passing runs. REMOVE THIS BLOCK once the cause is fixed.
import atexit as _atexit
import faulthandler as _faulthandler
import sys as _sys

_faulthandler.enable(file=_sys.stderr, all_threads=True)


def _debug_rank_atexit_marker():
    try:
        from bsb import MPI as _MPI

        _rank = _MPI.get_rank()
    except Exception:
        _rank = "?"
    _last_type = getattr(_sys, "last_type", None)
    _last_value = getattr(_sys, "last_value", None)
    _sys.stderr.write(
        f"[atexit-debug rank={_rank}] "
        f"last_exc={_last_type.__name__ if _last_type else None}: {_last_value}\n"
    )
    _sys.stderr.flush()


_atexit.register(_debug_rank_atexit_marker)
# === END TEMPORARY ===

from bsb_otel.testing import wrap_tests_with_traces  # noqa: E402


def load_tests(loader, tests, pattern):
    """
    Loads all the tests in the test suite and wraps the cases in otel traces.

    This method is called by the unittest module during test discovery.
    """

    # Use the pattern passed by the caller (e.g. via -p "test_connectivity2.py")
    # Fall back to the loader's default if none was given
    effective_pattern = pattern or loader.testNamePatterns or "test*.py"

    # Discover respecting the pattern, without top_level_dir to avoid
    # re-triggering this load_tests and looping infinitely
    suite = loader.discover("tests", pattern=effective_pattern)

    # Then visit the tree to wrap each test case in OTel logic
    wrap_tests_with_traces(suite)

    # Return the modified test suite
    return suite
