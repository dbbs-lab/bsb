from typing import Type

from errr.tree import exception as _e
from errr.tree import make_tree as _make_tree

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

PatchError: Type[Exception]
NotConnectableError: Type[PatchError]
NotConnectedError: Type[PatchError]
TransformError: Type[PatchError]
HocError: Type[PatchError]
HocConnectError: Type[HocError]
HocRecordError: Type[HocError]
HocSectionAccessError: Type[HocError]
SimulationError: Type[PatchError]
UninitializedError: Type[PatchError]
ErrorHandlingError: Type[PatchError]
ParallelError: Type[PatchError]
ParallelConnectError: Type[ParallelError]
BroadcastError: Type[ParallelError]
