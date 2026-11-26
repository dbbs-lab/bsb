"""
Make a parallel test run fail fast instead of hanging.

Under MPI, a test that fails on one rank only lets that rank skip the barriers and
collectives the other ranks still wait in, and the run hangs. Importing :mod:`bsb_test`
under MPI installs this watchdog on :class:`~unittest.TestResult`, so that it covers
every test of the run without any change to the tests:

* an error or failure on any rank prints that rank's traceback and aborts every rank;
* a test that runs longer than the timeout dumps the stack of every thread of the
  rank and exits it, which ends the run.

The timeout is ``BSB_TEST_TIMEOUT`` seconds per test (default 600). Set
``BSB_TEST_NO_WATCHDOG`` to disable the watchdog.
"""

import faulthandler as _faulthandler
import functools as _functools
import os as _os
import sys as _sys
import unittest as _unittest

from bsb import MPI

_DEFAULT_TIMEOUT = 600
_installed = False


def _abort(result, test, err):
    lines = result._exc_info_to_string(err, test)
    print(
        f"--- {test} FAILED ON RANK {MPI.get_rank()} (ABORTING ALL RANKS) ---\n",
        lines,
        file=_sys.stderr,
        flush=True,
    )
    MPI.abort(1)


def install(timeout=None):
    """
    Install the watchdog on :class:`~unittest.TestResult`.

    Does nothing in a serial run, when ``BSB_TEST_NO_WATCHDOG`` is set, or when the
    watchdog is already installed.

    :param float timeout: Seconds a single test may run before it counts as hung.
      Defaults to ``BSB_TEST_TIMEOUT``, or 600.
    """
    global _installed
    if _installed or "BSB_TEST_NO_WATCHDOG" in _os.environ:
        return
    if MPI.get_size() < 2:
        return
    if timeout is None:
        timeout = float(_os.environ.get("BSB_TEST_TIMEOUT", _DEFAULT_TIMEOUT))
    _patch(_unittest.TestResult, timeout)
    _installed = True


def _patch(result_cls, timeout):
    """
    Wrap the reporting methods of ``result_cls`` with the watchdog.

    :param type result_cls: :class:`~unittest.TestResult` or a subclass of it.
    :param float timeout: Seconds a single test may run before it counts as hung.
    """
    start_test = result_cls.startTest
    stop_test = result_cls.stopTest
    add_error = result_cls.addError
    add_failure = result_cls.addFailure
    add_subtest = result_cls.addSubTest

    @_functools.wraps(start_test)
    def startTest(self, test):
        _faulthandler.dump_traceback_later(timeout, exit=True)
        start_test(self, test)

    @_functools.wraps(stop_test)
    def stopTest(self, test):
        stop_test(self, test)
        _faulthandler.cancel_dump_traceback_later()

    @_functools.wraps(add_error)
    def addError(self, test, err):
        add_error(self, test, err)
        _abort(self, test, err)

    @_functools.wraps(add_failure)
    def addFailure(self, test, err):
        add_failure(self, test, err)
        _abort(self, test, err)

    @_functools.wraps(add_subtest)
    def addSubTest(self, test, subtest, err):
        add_subtest(self, test, subtest, err)
        if err is not None:
            _abort(self, subtest, err)

    result_cls.startTest = startTest
    result_cls.stopTest = stopTest
    result_cls.addError = addError
    result_cls.addFailure = addFailure
    result_cls.addSubTest = addSubTest


__all__ = ["install"]
