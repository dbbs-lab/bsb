"""
Serial MPI provider — emulates an MPI single-node context.

Selected when ``mpi4py`` is unavailable or the user explicitly prefers the
serial backend. Refuses to load if an MPI runtime is detected and
``BSB_IGNORE_PARALLEL`` is not set, to surface user mistakes that would
otherwise silently degrade to single-rank execution.
"""

import contextlib
import os

from ...exceptions import DependencyError, ProviderUnavailableError

if (
    any("mpi" in key.lower() for key in os.environ)
    and "BSB_IGNORE_PARALLEL" not in os.environ
):
    raise ProviderUnavailableError(
        "MPI runtime detected but the serial provider was selected. "
        "Install bsb[parallel] for MPI support, or set "
        "BSB_IGNORE_PARALLEL=1 to force the serial provider."
    )


class MPIService:
    """Serial mock of an MPI communicator."""

    def __init__(self, comm=None):
        if comm is not None:
            raise DependencyError(
                "Serial MPI provider does not accept a custom communicator."
            )
        self._comm = None

    def get_communicator(self):
        return None

    def get_rank(self):
        return 0

    def get_size(self):
        return 1

    def barrier(self):
        return None

    def abort(self, errorcode=1):
        print("MPI Abort called on MockCommunicator", flush=True)
        exit(errorcode)

    def bcast(self, obj, root=0):
        return obj

    def gather(self, obj, root=0):
        return [obj]

    def allgather(self, obj):
        return [obj]

    def window(self, buffer):
        return _WindowMock()

    @contextlib.contextmanager
    def try_all(self, default_exception=None):
        yield

    @contextlib.contextmanager
    def try_main(self):
        yield


class _WindowMock:
    def Get(self, bufspec, rank):
        return bufspec[0]

    def Lock(self, rank):
        pass

    def Unlock(self, rank):
        pass


MPI = MPIService()
"""MPI service singleton (serial mock)."""
