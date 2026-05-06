"""
Diagnostic import-time trace.

Prints a labelled line to stderr for every instrumented step. Default-on so
remote runs produce output without env tweaks. Set ``BSB_TRACE_IMPORTS=0`` to
silence.

Output format::

    [BSB-TRACE pid=12345 rank=0 t=  0.012s] services/__init__.py: pre  MPI = _MPIService()

The ``rank`` is read from common MPI launcher env vars BEFORE mpi4py is imported,
so it is available even on the very first line of the import sequence.
"""

import os
import sys
import time

_DISABLED = os.environ.get("BSB_TRACE_IMPORTS", "1") in ("0", "false", "False", "")
_T0 = time.monotonic()


def _rank():
    for var in (
        "OMPI_COMM_WORLD_RANK",
        "PMI_RANK",
        "PMIX_RANK",
        "SLURM_PROCID",
        "MPI_LOCALRANKID",
    ):
        v = os.environ.get(var)
        if v is not None:
            return v
    return "?"


def t(msg):
    if _DISABLED:
        return
    dt = time.monotonic() - _T0
    sys.stderr.write(
        f"[BSB-TRACE pid={os.getpid()} rank={_rank()} t={dt:8.3f}s] {msg}\n"
    )
    sys.stderr.flush()


t("_trace.py: module loaded")


# Build banner — printed on every load, regardless of BSB_TRACE_IMPORTS, so we
# can verify from the HPC collaborator's log that the right commit is running.
# Bump _BUILD on every edit to anything in this debug branch.
_BUILD = 1
_BRANCH = "debug/mpi-init-import-trace"
sys.stderr.write(
    f"\n============== RUNNING TRACES "
    f"[enabled={'true' if not _DISABLED else 'false'}, "
    f"build={_BUILD}, branch={_BRANCH}] ==============\n"
)
sys.stderr.flush()
