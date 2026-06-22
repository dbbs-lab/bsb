"""
Serial Pool provider — runs submitted callables synchronously in-process.

Conforms to :class:`bsb.services.pool.PoolExecutor`. Useful as a default
fallback when no MPI-aware concurrency backend is installed.
"""

import concurrent.futures


class Pool(concurrent.futures.Executor):
    """Synchronous, in-process executor."""

    def __init__(self, *, loglevel=None, debug: bool = False, **_kwargs):
        self._open = True

    @property
    def open(self) -> bool:
        return self._open

    def is_worker(self) -> bool:
        return False

    def submit(self, fn, /, *args, **kwargs):
        if not self._open:
            raise RuntimeError("Cannot submit to a closed pool.")
        future: concurrent.futures.Future = concurrent.futures.Future()
        if not future.set_running_or_notify_cancel():
            return future
        try:
            result = fn(*args, **kwargs)
        except BaseException as exc:
            future.set_exception(exc)
        else:
            future.set_result(result)
        return future

    def shutdown(self, wait=True, *, cancel_futures=False):
        self._open = False
