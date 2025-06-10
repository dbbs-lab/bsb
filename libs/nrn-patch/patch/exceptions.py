from errr import exception as _e
from errr import make_tree as _make_tree

_make_tree(
    globals(),
    PatchError=_e(
        NotConnectableError=_e(),
        NotConnectedError=_e(),
        TransformError=_e(),
        HocError=_e(
            HocConnectError=_e(), HocRecordError=_e(), HocSectionAccessError=_e()
        ),
        SimulationError=_e(),
        UninitializedError=_e(),
        ErrorHandlingError=_e(),
        ParallelError=_e(
            ParallelConnectError=_e(),
            BroadcastError=_e(),
        ),
    ),
)

__all__ = [
    "PatchError",
    "NotConnectableError",
    "NotConnectedError",
    "TransformError",
    "HocError",
    "HocConnectError",
    "HocRecordError",
    "HocSectionAccessError",
    "SimulationError",
    "UninitializedError",
    "ErrorHandlingError",
    "ParallelError",
    "ParallelConnectError",
    "BroadcastError",
]
