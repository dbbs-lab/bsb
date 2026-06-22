"""
Pool (concurrent executor) service contract (stub).

This is the *thin* pool service: a swappable concurrency backend that submits
callables and returns futures. The thick workflow machinery (``JobPool``,
job dependencies, ``pool_cache``, listeners) lives in :mod:`bsb.jobs` and
consumes the executor exposed here.

A provider module must expose:

* ``Pool``: a class (or callable) returning a :class:`PoolExecutor`.

A :class:`PoolExecutor` extends :class:`concurrent.futures.Executor` with two
hooks used by the thick :class:`bsb.jobs.JobPool` to drive
collective-coordination backends like ``mpipool``:

* ``is_worker()`` — return ``True`` on ranks that should not schedule. For
  shared-submit backends (``multiprocessing``, ``serial``) this always
  returns ``False``.
* ``open`` — ``True`` while the pool accepts submissions, ``False`` after
  ``shutdown``.

Reference stub — the runtime module is installed by
``bsb.services.__init__``.
"""

from __future__ import annotations

import concurrent.futures
import typing
from typing import Any, Protocol


class PoolExecutor(Protocol):
    @property
    def open(self) -> bool: ...
    def is_worker(self) -> bool: ...
    def submit(
        self, fn: typing.Callable[..., Any], /, *args: Any, **kwargs: Any
    ) -> concurrent.futures.Future: ...
    def shutdown(self, wait: bool = True, *, cancel_futures: bool = False) -> None: ...


if typing.TYPE_CHECKING:  # pragma: nocover

    class Pool(PoolExecutor):
        def __init__(self, **kwargs: Any) -> None: ...
