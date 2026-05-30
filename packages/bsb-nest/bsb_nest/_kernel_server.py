"""
Standalone NEST kernel server.

Launched by file path (``python .../_kernel_server.py <socket>``) so it runs as
an independent process: it never inherits the parent's NEST/MPI state, never
re-imports the parent's ``__main__``, and imports ``nest`` only on its own main
thread. The build process talks to it over a
:mod:`multiprocessing.connection` pipe.

Kept free of ``bsb_nest`` (and any non-stdlib) imports at module level so the
file can be executed directly without importing the package.
"""

import os
import sys


class _Kernel:
    """Main-thread wrapper around ``nest`` in the server process.

    Methods return only basic Python types so they pickle cleanly back to the
    build process; NEST's SLI objects are not picklable.
    """

    def __init__(self):
        import nest

        self._nest = nest
        self._loaded = set()

    def install(self, module):
        try:
            self._nest.Install(module)
        except Exception as e:
            # Re-installing a module is benign; surface any other failure.
            if getattr(e, "errorname", "") == "DynamicModuleManagementError" and (
                "loaded already" in getattr(e, "message", "")
            ):
                return
            raise

    def load_modules(self, modules):
        """Install NEST *modules*, skipping any already loaded for this build.

        Returns the names of any *modules* that could not be found, so the
        caller can turn them into a configuration error. One server is reused
        for the whole build, so tracking what is loaded keeps each module's
        ``Install`` to a single call.
        """
        missing = []
        for module in modules:
            if module in self._loaded:
                continue
            try:
                self.install(module)
            except Exception as e:
                if getattr(e, "errorname", "") == "DynamicModuleManagementError" and (
                    "file not found" in getattr(e, "message", "")
                ):
                    missing.append(module)
                    continue
                raise
            self._loaded.add(module)
        return missing

    def has_delay(self, model):
        return bool(self._nest.GetDefaults(model)["has_delay"])

    def models(self, mtype=None):
        ms = self._nest.Models(mtype=mtype) if mtype else self._nest.Models()
        return [str(m) for m in ms]


def serve(address, authkey):
    """Bind *address* and answer kernel requests until told to stop."""
    from multiprocessing.connection import Listener

    kernel = _Kernel()  # imports nest on this process's main thread
    with Listener(address, authkey=authkey) as listener:
        conn = listener.accept()
        with conn:
            while True:
                try:
                    method, args = conn.recv()
                except EOFError:
                    break
                if method == "__stop__":
                    conn.send(("ok", None))
                    break
                try:
                    conn.send(("ok", getattr(kernel, method)(*args)))
                except BaseException as e:
                    conn.send(
                        ("err", (type(e).__name__, getattr(e, "errorname", ""), str(e)))
                    )


if __name__ == "__main__":
    serve(sys.argv[1], bytes.fromhex(os.environ["_BSB_NEST_KERNEL_AUTHKEY"]))
