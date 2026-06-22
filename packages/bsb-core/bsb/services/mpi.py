"""
MPI service contract (stub).

This module is a *reference stub*. At runtime, ``bsb.services.__init__`` resolves
an MPI provider (e.g. ``bsb._providers.mpi.mpi4py`` or ``.serial``) and
installs it into ``sys.modules['bsb.services.mpi']`` before any consumer can
import it, so the body below is never executed.

A provider module must expose:

* ``MPI``: an instance satisfying :class:`MPIProtocol` below.
* ``MPIService``: the class used to build per-communicator wrappers (used by
  storage engines that need a custom communicator).
"""

from __future__ import annotations

import typing
from typing import Any, Protocol


class MPIProtocol(Protocol):
    """Communicator abstraction every MPI provider must implement."""

    def get_communicator(self) -> Any: ...
    def get_rank(self) -> int: ...
    def get_size(self) -> int: ...
    def barrier(self) -> None: ...
    def abort(self, errorcode: int = 1) -> None: ...
    def bcast(self, obj: Any, root: int = 0) -> Any: ...
    def gather(self, obj: Any, root: int = 0) -> list[Any]: ...
    def allgather(self, obj: Any) -> list[Any]: ...
    def window(self, buffer: Any) -> Any: ...
    def try_all(self, default_exception: Exception | None = None) -> Any: ...
    def try_main(self) -> Any: ...


if typing.TYPE_CHECKING:  # pragma: nocover
    MPI: MPIProtocol

    class MPIService(MPIProtocol): ...
