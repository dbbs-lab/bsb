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
import contextlib as _contextlib
import faulthandler as _faulthandler
import os as _os
import signal as _signal
import sys as _sys
import threading as _threading
import time as _time

# Default faulthandler set: SIGSEGV/SIGABRT/SIGBUS/SIGFPE/SIGILL.
# Add SIGTERM/SIGINT/SIGHUP so a peer-rank kill from mpiexec dumps a stack
# instead of vanishing. The bsb-core test target also sets the OpenMPI MCA
# parameter `orte_timeout_usec_between_signals` to 15s so the SIGTERM
# handler has time to actually run before SIGKILL arrives.
_faulthandler.enable(file=_sys.stderr, all_threads=True)
for _sig in (_signal.SIGTERM, _signal.SIGINT, _signal.SIGHUP):
    with _contextlib.suppress(Exception):
        _faulthandler.register(_sig, file=_sys.stderr, all_threads=True, chain=True)


# Rank-tagged heartbeat: every 30s prints [heartbeat rank=N pid=P] then a full
# stack dump. Lets us identify which rank stops emitting first → confirms (or
# disproves) the "rank 0 finishes faster, mpiexec then kills rank 1" theory.
def _rank_tagged_heartbeat():
    # 10s heartbeat so at least one fires within the 15s SIGTERM→SIGKILL
    # grace window from `--mca orte_timeout_usec_between_signals 15000000`,
    # guaranteeing we capture rank 1's state right before death.
    while True:
        _time.sleep(10)
        try:
            from bsb import MPI as _MPI

            _rank = _MPI.get_rank()
        except Exception:
            _rank = "?"
        _sys.stderr.write(
            f"[heartbeat rank={_rank} pid={_os.getpid()} t={_time.monotonic():.1f}s]\n"
        )
        _sys.stderr.flush()
        _faulthandler.dump_traceback(file=_sys.stderr, all_threads=True)


_threading.Thread(target=_rank_tagged_heartbeat, daemon=True).start()


def _debug_rank_atexit_marker():
    try:
        from bsb import MPI as _MPI

        _rank = _MPI.get_rank()
    except Exception:
        _rank = "?"
    _last_type = getattr(_sys, "last_type", None)
    _last_value = getattr(_sys, "last_value", None)
    # Best-effort exit code: SystemExit value if propagating, else None.
    _exit_code = (
        _last_value.code
        if isinstance(_last_value, SystemExit)
        else None
    )
    _sys.stderr.write(
        f"[atexit-debug rank={_rank} pid={_os.getpid()}] "
        f"last_exc={_last_type.__name__ if _last_type else None}: {_last_value} "
        f"exit_code={_exit_code}\n"
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
