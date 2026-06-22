"""
MPILock service contract (stub).

Reference stub — the runtime module is installed by
``bsb.services.__init__``. A provider module must expose:

* ``MPILock``: a callable taking ``(comm=None, master=0)`` returning a
  controller that yields read/write/single_write locks.
"""

from __future__ import annotations

import typing
from typing import Any, Protocol


class MPILockController(Protocol):
    @property
    def master(self) -> int: ...
    @property
    def rank(self) -> int: ...
    @property
    def closed(self) -> bool: ...
    def close(self) -> None: ...
    def __enter__(self) -> "MPILockController": ...
    def __exit__(self, *exc: Any) -> None: ...
    def read(self) -> Any: ...
    def write(self) -> Any: ...
    def single_write(self, handle: Any = None, rank: int | None = None) -> Any: ...


class MPILockFactory(Protocol):
    def sync(self, comm: Any = None, master: int = 0) -> MPILockController: ...
    def __call__(
        self, comm: Any = None, master: int | None = None
    ) -> MPILockController: ...


if typing.TYPE_CHECKING:  # pragma: nocover
    MPILock: MPILockFactory
