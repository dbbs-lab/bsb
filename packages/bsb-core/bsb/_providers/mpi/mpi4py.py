"""
MPI service provider backed by ``mpi4py``.

Loaded by :mod:`bsb._providers.mpi.mpi4py_loader` only after mpi4py
availability has been verified.
"""

import contextlib

from mpi4py.MPI import COMM_WORLD, INFO_NULL, Win


class MPIService:
    """MPI communicator wrapper backed by mpi4py."""

    def __init__(self, comm=None):
        self._comm = comm if comm is not None else COMM_WORLD

    def get_communicator(self):
        return self._comm

    def get_rank(self):
        return self._comm.Get_rank()

    def get_size(self):
        return self._comm.Get_size()

    def barrier(self):
        return self._comm.Barrier()

    def abort(self, errorcode=1):
        return self._comm.Abort(errorcode)

    def bcast(self, obj, root=0):
        return self._comm.bcast(obj, root=root)

    def gather(self, obj, root=0):
        return self._comm.gather(obj, root=root)

    def allgather(self, obj):
        return self._comm.allgather(obj)

    def window(self, buffer):
        if self.get_size() > 1:
            return Win.Create(buffer, True, INFO_NULL, self._comm)
        return _WindowMock()

    @contextlib.contextmanager
    def try_all(self, default_exception=None):
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
        exc_instance = None
        try:
            yield
        except Exception as e:
            exc_instance = e

        exception = self.bcast(exc_instance)
        if exception is not None:
            raise exception


class _WindowMock:
    def Get(self, bufspec, rank):
        return bufspec[0]

    def Lock(self, rank):
        pass

    def Unlock(self, rank):
        pass


MPI = MPIService()
"""MPI service singleton."""
