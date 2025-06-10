import _shared
from neuron import h

from patch import p
from patch.error_handler import (
    CatchNetCon,
    ErrorHandler,
    _suppress_nrn,
    catch_hoc_error,
)
from patch.exceptions import ErrorHandlingError, HocConnectError, HocError


class TestErrorHandling(_shared.NeuronTestCase):
    """
    Test whether the error handling system functions.
    """

    def test_hoc_handler(self):
        def test():
            with catch_hoc_error():
                v = p.Vector()
                v.__neuron__().record(p.Section())

        with self.assertRaises(HocError, msg="Did not capture `RuntimeError: hoc error`"):
            test()

    def test_handler_requirements(self):
        def test():
            with catch_hoc_error(CatchNetCon):
                h.NetCon(5, 12)

        with self.assertRaises(
            ErrorHandlingError,
            msg="Did not complain about missing handler requirements",
        ):
            test()

        class UndefinedRequirements(ErrorHandler):
            def catch(self, error, context):  # pragme: nocover
                pass

        def test_undef():
            with catch_hoc_error(UndefinedRequirements):
                h.NetCon(5, 12)

        with self.assertRaises(
            ErrorHandlingError,
            msg="Did not complain about undefined handler requirements",
        ):
            test_undef()

    def test_netcon_errors(self):
        s = p.Section()
        t = p.Vector()
        with self.assertRaises(HocConnectError, msg="Didn't catch NetCon error"):
            p.NetCon(s, t)
        with self.assertRaises(HocConnectError, msg="Didn't catch NetCon error"):
            p.NetCon(t, s)
        with self.assertRaises(HocConnectError, msg="Didn't catch NetCon error"):
            p.NetCon(5, 12)

    def test_suppress(self):
        with _suppress_nrn():
            print("ERROR! SUPPRESSION FAILED!")

    def test_error_handling_error(self):
        class BrokenHandler(ErrorHandler):
            required = []

            def catch(self, error, context):
                raise Exception("I crashed")

        with self.assertRaises(ErrorHandlingError), catch_hoc_error(BrokenHandler):
            h.NetCon(5, 12)

    def test_missing_handle(self):
        class NoCatchHandler(ErrorHandler):
            required = []

        with self.assertRaises(ErrorHandlingError), catch_hoc_error(NoCatchHandler):
            h.NetCon(5, 12)
