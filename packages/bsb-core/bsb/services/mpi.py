import contextlib
import functools
import os

from ..exceptions import DependencyError
from ._util import MockModule


class MPIService:
    """
    Interface for MPI Communication context.

    This class will also emulate MPI Communication context in single node context.
    """

    def __init__(self, comm=None):
        self._mpi = MPIModule("mpi4py.MPI")
        self._comm = comm or self._mpi.COMM_WORLD

    def get_communicator(self):
        return self._comm

    def get_rank(self):
        if self._comm:
            return self._comm.Get_rank()
        return 0

    def get_size(self):
        if self._comm:
            return self._comm.Get_size()
        return 1

    def barrier(self):
        if self._comm:
            return self._comm.Barrier()
        pass

    def abort(self, errorcode=1):
        if self._comm:
            return self._comm.Abort(errorcode)
        print("MPI Abort called on MockCommunicator", flush=True)
        exit(errorcode)

    def bcast(self, obj, root=0):
        if self._comm:
            return self._comm.bcast(obj, root=root)
        return obj

    def gather(self, obj, root=0):
        if self._comm:
            return self._comm.gather(obj, root=root)
        return [obj]

    def allgather(self, obj):
        if self._comm:
            return self._comm.allgather(obj)
        return [obj]

    def window(self, buffer):
        if self._comm and self.get_size() > 1:
            from mpi4py.MPI import INFO_NULL, Win

            return Win.Create(buffer, True, INFO_NULL, self._comm)
        else:

            class WindowMock:
                def Get(self, bufspec, rank):
                    return bufspec[0]

                def Lock(self, rank):
                    pass

                def Unlock(self, rank):
                    pass

            return WindowMock()

    @contextlib.contextmanager
    def try_all(self, default_exception=None):
        """
        Create a context manager that checks if any exception is raised by any processes
        within the context, and make all other processes raise an exception in that case

        :param Exception default_exception: Exception instance to raise for all processes
          that did not raise during the context.
        :return: context manager
        """
        exc_instance = None
        default_exception = default_exception or RuntimeError(
            "An error occurred on a different rank"
        )
        try:
            yield
        except Exception as e:
            exc_instance = e

        exceptions = self.allgather(exc_instance)
        if any(exceptions):
            raise (
                exceptions[self.get_rank()]
                if exceptions[self.get_rank()]
                else default_exception
            )

    @contextlib.contextmanager
    def try_main(self):
        """
        Create a context manager that checks if any exception is raised by the main
        process within the context, and make all other processes raise this exception in
        that case
        Warning: All processes will still enter the context, but only main exception will
        be raised.

        :return: context manager
        """
        exc_instance = None
        try:
            # All processes have to enter the context
            # contextlib will throw an error if one does not yield
            yield
        except Exception as e:
            exc_instance = e

        exception = self.bcast(exc_instance)
        if exception is not None:
            raise exception


class MPIModule(MockModule):
    """
    Module provider of the MPI interface.
    """

    @property
    @functools.cache
    def COMM_WORLD(self):
        if (
            any("mpi" in key.lower() for key in os.environ)
            and "BSB_IGNORE_PARALLEL" not in os.environ
        ):
            raise DependencyError(
                "MPI runtime detected without parallel support."
                + " Please install with `pip install bsb[parallel]`."
                + " Set `BSB_IGNORE_PARALLEL` to ignore this error."
            )
        return None
