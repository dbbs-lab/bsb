import http.client as _http
import threading as _threading
import unittest as _unittest

from bsb import MPI

_mpi_size = MPI.get_size()


def internet_connection():
    for ip in ("1.1.1.1", "8.8.8.8"):
        conn = _http.HTTPSConnection(ip, timeout=2)
        try:
            _http.request("HEAD", "/")
            return True
        except Exception:
            pass
        finally:
            conn.close()
    else:
        return False


def skip_nointernet(o):
    return _unittest.skipIf(not internet_connection(), "Internet connection required.")(o)


def skip_serial(o):
    return _unittest.skipIf(_mpi_size == 1, "Skipped during serial testing.")(o)


def skip_parallel(o):
    return _unittest.skipIf(_mpi_size > 1, "Skipped during parallel testing.")(o)


_exc_threads = {}


def _excepthook(f):
    def catcher(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except Exception as e:
            h = hash(_threading.current_thread())
            _exc_threads[h] = e

    return catcher


def timeout(timeout, abort=False):
    def decorator(f):
        def timed_f(*args, **kwargs):
            thread = _threading.Thread(
                target=_excepthook(f), args=args, kwargs=kwargs, daemon=True
            )
            thread.start()
            thread.join(timeout=timeout)
            try:
                if thread.is_alive():
                    err = TimeoutError(
                        1,
                        f"{f.__name__} timed out on rank {MPI.get_rank()}",
                        args,
                        kwargs,
                    )
                    raise err
                elif hash(thread) in _exc_threads:
                    e = _exc_threads[hash(thread)]
                    del _exc_threads[hash(thread)]
                    raise e
            except Exception as e:
                if MPI.get_size() > 1 and abort:
                    import sys
                    import traceback

                    errlines = traceback.format_exception(type(e), e, e.__traceback__)
                    print(
                        "--- EXCEPTION UNDER MPI (ABORTING) ---\n",
                        *errlines,
                        file=sys.stderr,
                        flush=True,
                    )
                    MPI.abort(1)
                else:
                    raise

        return timed_f

    return decorator


def on_main_only(f):
    def main_wrapper(*args, **kwargs):
        if MPI.get_rank():
            MPI.barrier()
        else:
            r = f(*args, **kwargs)
            MPI.barrier()
            return r

    return main_wrapper


def serial_setup(cls):
    cls.setUp = on_main_only(cls.setUp)
    return cls


__all__ = [
    "MPI",
    "internet_connection",
    "skip_nointernet",
    "skip_serial",
    "skip_parallel",
    "timeout",
    "on_main_only",
    "serial_setup",
]
