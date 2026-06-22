"""
Pool provider backed by ``mpipool.MPIExecutor``.

Provides a collective-coordination executor: rank 0 schedules jobs, other ranks
are workers that block in ``MPIExecutor.__init__`` until shutdown.
"""

import mpipool as _mpipool
from mpipool import MPIExecutor as _MPIExecutor


class Pool(_MPIExecutor):
    """Thin wrapper exposing the BSB pool contract over ``mpipool.MPIExecutor``."""

    def __init__(self, *, loglevel=None, debug: bool = False, **kwargs):
        if debug:
            _mpipool.enable_serde_logging()
        if loglevel is not None:
            kwargs.setdefault("loglevel", loglevel)
        super().__init__(**kwargs)
