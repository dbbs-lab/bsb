"""
Diagnostic import-time trace with process-identity fingerprint.

Default-on; set BSB_TRACE_IMPORTS=0 to silence.

Each log line carries a process fingerprint ``fp=PID.STARTTIME``. STARTTIME is
read from ``/proc/self/stat`` field 22 (clock ticks since boot when the process
started). PID+STARTTIME uniquely identifies a Linux process — it survives PID
reuse, but is PRESERVED across ``exec()``. So when comparing two waves of
output:

   same ``fp``                  → same OS process (possibly post-exec if cmdline differs)
   same ``pid``, diff ``fp``    → different OS process, PID was reused

Also installs:
   - one-time BSB-TRACE-INFO dump: self.cmdline, parent.cmdline, sys.argv,
     sys.executable, session/pgid, SLURM/OMPI/PMI*/OTEL*/BSB* env vars
   - atexit hook ........... logs orderly interpreter exit (with current exception, if any)
   - signal handler ........ logs SIGTERM/SIGINT/SIGHUP/SIGUSR{1,2}/SIGQUIT/SIGABRT then re-raises
   - audit hook ............ logs os.exec*, os.fork*, os.posix_spawn, os.system, os.kill, subprocess.Popen
   - sys.excepthook wrapper. logs unhandled exceptions before Python tears down
"""

import atexit
import os
import signal
import sys
import time

_DISABLED = os.environ.get("BSB_TRACE_IMPORTS", "1") in ("0", "false", "False", "")
_T0 = time.monotonic()
_WALL0 = time.time()


def _safe_read(path):
    try:
        with open(path, "rb") as f:
            return f.read()
    except Exception as e:  # noqa: BLE001
        return f"<read failed: {e!r}>".encode()


def _read_starttime(pid="self"):
    raw = _safe_read(f"/proc/{pid}/stat")
    try:
        s = raw.decode("utf-8", "replace")
        # field 2 is "(comm)" which can contain spaces/parens; rfind ')' to skip it
        rest = s[s.rfind(")") + 2 :]
        # field 22 in /proc/<pid>/stat is starttime. We've already consumed fields 1+2,
        # so it's index 19 in the remaining whitespace-split.
        return rest.split()[19]
    except Exception:  # noqa: BLE001
        return "?"


def _read_cmdline(pid):
    raw = _safe_read(f"/proc/{pid}/cmdline")
    if isinstance(raw, bytes):
        return " ".join(p.decode("utf-8", "replace") for p in raw.split(b"\0") if p)
    return str(raw)


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


_PID = os.getpid()
_PPID = os.getppid()
_STARTTIME = _read_starttime("self")
_FP = f"{_PID}.{_STARTTIME}"


def t(msg):
    if _DISABLED:
        return
    dt = time.monotonic() - _T0
    sys.stderr.write(
        f"[BSB-TRACE pid={_PID} ppid={_PPID} fp={_FP} rank={_rank()} t={dt:8.3f}s] {msg}\n"
    )
    sys.stderr.flush()


def _info(msg):
    if _DISABLED:
        return
    sys.stderr.write(
        f"[BSB-TRACE-INFO pid={_PID} ppid={_PPID} fp={_FP} rank={_rank()}] {msg}\n"
    )
    sys.stderr.flush()


def _on_exit():
    exc = sys.exc_info()[0]
    t(
        f"_trace.py: atexit — interpreter exiting "
        f"(current_exc={exc.__name__ if exc else None})"
    )


def _on_signal(signum, frame):
    try:
        name = signal.Signals(signum).name
    except Exception:  # noqa: BLE001
        name = "?"
    t(
        f"_trace.py: signal received signum={signum} ({name}) — "
        f"restoring SIG_DFL and re-raising"
    )
    try:
        signal.signal(signum, signal.SIG_DFL)
        os.kill(_PID, signum)
    except Exception:  # noqa: BLE001
        pass


def _audit(event, args):
    if event in (
        "os.exec",
        "os.fork",
        "os.forkpty",
        "os.posix_spawn",
        "os.spawn",
        "os.system",
        "os.kill",
        "subprocess.Popen",
    ):
        try:
            t(f"_trace.py: audit event={event} args={args!r}")
        except Exception:  # noqa: BLE001
            pass


_orig_excepthook = sys.excepthook


def _excepthook(exc_type, exc_value, exc_tb):
    try:
        t(
            f"_trace.py: sys.excepthook — unhandled "
            f"{exc_type.__name__}: {exc_value!r}"
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        _orig_excepthook(exc_type, exc_value, exc_tb)
    except Exception:  # noqa: BLE001
        pass


def _filtered_env():
    keys = sorted(
        k
        for k in os.environ
        if k.startswith(("SLURM_", "OMPI_", "PMI_", "PMIX_", "PMI2_", "OTEL_", "BSB_"))
        or k in ("MPI_LOCALRANKID", "OMP_NUM_THREADS", "PYTHONPATH")
    )
    return {k: os.environ[k] for k in keys}


# Install lifecycle hooks BEFORE the info dump, so even if the dump fails we
# still capture exits/signals/excepts.
atexit.register(_on_exit)
for _sig in (
    signal.SIGTERM,
    signal.SIGINT,
    signal.SIGHUP,
    signal.SIGUSR1,
    signal.SIGUSR2,
    signal.SIGQUIT,
    signal.SIGABRT,
):
    try:
        signal.signal(_sig, _on_signal)
    except Exception:  # noqa: BLE001
        pass
try:
    sys.addaudithook(_audit)
except Exception:  # noqa: BLE001
    pass
sys.excepthook = _excepthook

# One-time dump of process identity & launcher context.
if not _DISABLED:
    _info(f"sys.executable={sys.executable!r}")
    _info(f"sys.argv={sys.argv!r}")
    _info(f"self.cmdline={_read_cmdline(_PID)!r}")
    _info(f"parent.cmdline={_read_cmdline(_PPID)!r}")
    _info(f"wall_clock_unix={_WALL0:.6f}")
    try:
        _info(f"sid={os.getsid(0)} pgid={os.getpgrp()}")
    except Exception:  # noqa: BLE001
        pass
    _info(f"_trace.py.__file__={__file__!r}")
    _info(f"env (filtered)={_filtered_env()}")

t("_trace.py: module loaded")


# Build banner — printed on every load, regardless of BSB_TRACE_IMPORTS, so we
# can verify from the HPC collaborator's log that the right commit is running.
# Bump _BUILD on every edit to anything in this debug branch.
_BUILD = 1
_BRANCH = "debug/mpi-trace-fingerprint"
sys.stderr.write(
    f"\n============== RUNNING TRACES "
    f"[enabled={'true' if not _DISABLED else 'false'}, "
    f"build={_BUILD}, branch={_BRANCH}] ==============\n"
)
sys.stderr.flush()
