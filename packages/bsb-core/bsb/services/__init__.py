"""
Service module.

Register or access interfaces that may be provided, mocked or missing, but should always
behave neatly on import.
"""

# fmt: off
# isort: off
from .._trace import t as _t  # noqa: E402

_t("bsb/services/__init__.py: enter")

_t("bsb/services/__init__.py: pre  from ._util import ErrorModule as _ErrorModule")
from ._util import ErrorModule as _ErrorModule  # noqa: E402
_t("bsb/services/__init__.py: post from ._util import ErrorModule as _ErrorModule")

_t("bsb/services/__init__.py: pre  from .mpi import MPIService as _MPIService")
from .mpi import MPIService as _MPIService  # noqa: E402
_t("bsb/services/__init__.py: post from .mpi import MPIService as _MPIService")

_t("bsb/services/__init__.py: pre  from .mpilock import MPILockModule as _MPILockModule")
from .mpilock import MPILockModule as _MPILockModule  # noqa: E402
_t("bsb/services/__init__.py: post from .mpilock import MPILockModule as _MPILockModule")

_t("bsb/services/__init__.py: pre  MPI = _MPIService()  *** MPI_INIT FIRES INSIDE THIS CALL ***")
MPI = _MPIService()
_t("bsb/services/__init__.py: post MPI = _MPIService()")
"""
MPI service.
"""
_t("bsb/services/__init__.py: pre  MPILock = _MPILockModule('mpilock')")
MPILock = _MPILockModule("mpilock")
_t("bsb/services/__init__.py: post MPILock = _MPILockModule('mpilock')")
"""
MPILock service.
"""

_t("bsb/services/__init__.py: pre  from .pool import JobPool as _JobPool")
from .pool import JobPool as _JobPool  # noqa E402  # needs to be imported after MPIService
_t("bsb/services/__init__.py: post from .pool import JobPool as _JobPool")
_t("bsb/services/__init__.py: pre  from .pool import WorkflowError, pool_cache")
from .pool import WorkflowError, pool_cache  # noqa E402  # needs to be imported after MPIService
_t("bsb/services/__init__.py: post from .pool import WorkflowError, pool_cache")
# fmt: on
# isort: on

JobPool = _JobPool
"""
JobPool service.
"""


def __getattr__(attr):
    return _ErrorModule(f"{attr} is not a registered service.")


def register_service(attr, provider):
    globals()[attr] = provider


__all__ = [
    "MPI",
    "MPILock",
    "JobPool",
    "register_service",
    "WorkflowError",
    "pool_cache",
]

_t("bsb/services/__init__.py: module fully loaded")
