"""
MPILock provider backed by the ``mpilock`` package.

The actual ``mpilock`` module already exposes ``sync()`` and ``WindowController``,
so we expose it directly through the ``MPILock`` symbol.
"""

import mpilock as _mpilock

MPILock = _mpilock
"""MPILock service — the real mpilock module."""
