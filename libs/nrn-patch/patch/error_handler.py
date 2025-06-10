import io
import os
import sys
from contextlib import contextmanager

from patch.exceptions import (
    ErrorHandlingError,
    HocConnectError,
    HocError,
    HocRecordError,
    HocSectionAccessError,
    PatchError,
)


@contextmanager
def _suppress_nrn(stream=None, close=False):
    """
    Makes NEURON logging silent.
    """
    if stream is None:
        # stream was not provided as parameter so we initialize it
        # and close it after yield
        stream = open(os.devnull, "w")  # noqa: SIM115
        close = True
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = stream
    sys.stderr = stream
    try:
        yield
    finally:
        if close:
            stream.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr


@contextmanager
def catch_hoc_error(*args, **context):
    with io.StringIO() as error_stream:
        try:
            with _suppress_nrn(error_stream):
                yield
        except RuntimeError as e:
            error = error_stream.getvalue()
            try:
                for handler in args:
                    handler(error, context)
            except Exception as e:
                raise e from None
            # Uncaught HocError
            if "hoc error" in str(e) or "hocobj_call error" in str(e):
                raise HocError(error) from None
            # Actual RuntimeError
            raise e from None  # pragma: nocover


class ErrorHandler:
    """
    Base error handler class.

    The class object is "callable" and takes the arguments that an error handle callable
    should take. This means that when the class is passed in the argument list of
    ``catch_hoc_error`` that we'll construct an object;

    The constructor checks whether the context contains enough information for us to
    handle the error and calls its ``catch`` method that you need to override. Inside of
    the catch method you can analyze the error message and context and raise a polished
    version of the error. All raised errors must inherit from ``patch.object.PatchError``
    or they'll be treated as a failure of the error handler and an ``ErrorHandlingError``
    will be raised on top of it.

    To specify the required items of the context create a class attribute list
    ``required``::

      class A(ErrorHandler):
          required = ["info_i_need_to_operate"]

    Whenever the error handler class ``A`` is used, the ``catch_hoc_error`` call will
    have the specify the keyword argument ``info_i_need_to_operate``.
    """

    def __init__(self, error, context):
        if not hasattr(self.__class__, "required"):
            raise ErrorHandlingError(
                f"Error context requirements missing for {self.__class__.__name__}"
            )
        for required_item in self.__class__.required:
            if required_item not in context:
                raise ErrorHandlingError(
                    f"Required error context item '{required_item}' for "
                    f"{self.__class__.__name__} is missing"
                )
        self.__dict__.update(context)
        try:
            self.catch(error, context)
        except PatchError:
            raise
        except Exception:
            raise ErrorHandlingError(
                f"{self.__class__.__name__} errored out during error handling."
            ) from None

    def catch(self, error, context):
        raise ErrorHandlingError(
            f"Catch method not implemented for {self.__class__.__name__}"
        )


def detector(error):
    """
    Pass this the error message and it returns a lambda function that you can pass a
    string.

    Returns ``True`` if the string occurs in the error message, ``False``
    otherwise.
    """
    return lambda trigger: error.lower().find(trigger) != -1


class CatchNetCon(ErrorHandler):
    """
    Catches a variety of errors that can occur when using ``h.NetCon`` and raises
    ``HocConnectError``.
    """

    required = ["nrn_source", "nrn_target"]

    def catch(self, error, context):
        e = detector(error)
        if e("must be a point process or nullobject"):
            if e("arg 1"):
                raise HocConnectError(
                    "Source is not a point process. Transformed type: "
                    f"'{type(self.nrn_source)}'"
                )
            if e("arg 2"):
                raise HocConnectError(
                    "Target is not a point process. Transformed type: "
                    f"'{type(self.nrn_target)}'"
                )
        if e("interpreter stack type error"):
            raise HocConnectError(
                f"Incorrect types passed to NetCon. Source: {type(self.nrn_source)}, "
                f"target: {type(self.nrn_target)}"
            )


# Section access errors can't be triggered without NEURON exiting:
# https://github.com/neuronsimulator/nrn/issues/769
class CatchSectionAccess(ErrorHandler):  #  pragma: nocover
    """
    Catches errors that occur when the Section stack is empty and accessed, raises
    ``HocSectionAccessError``.
    """

    required = []

    def catch(self, error, context):
        e = detector(error)
        if e("Section access unspecified"):
            raise HocSectionAccessError(
                "This operation requires a Section on the stack "
                "or perhaps a `sec` keyword argument."
            )


class CatchRecord(ErrorHandler):
    """
    Catches a variety of errors that occur when using ``h.Vector().record``, raises
    ``HocRecordError``.
    """

    required = ["target"]

    def catch(self, error, context):
        e = detector(error)
        if e("first arg is not a point_process") or e("interpreter stack type error"):
            raise HocRecordError(
                f"Can't record {self.target}, its record pointer is not a point process."
            )
        # Encountered this error locally, most likely on NEURON 7.7, don't cover
        if e("number was provided instead of a pointer"):  #  pragma: nocover
            raise HocRecordError(
                f"Can't record {self.target}, its record pointer is a value. "
                "Make sure that you're recording `y._ref_x` rather than `y.x`."
            )
