from errr.tree import exception as _e
from errr.tree import make_tree as _make_tree

_make_tree(
    globals(),
    ArborizeError=_e(
        ModelDefinitionError=_e("definition"),
        ModelError=_e(
            "model",
            TransmitterError=_e("section"),
            UnknownLocationError=_e("location"),
            UnknownSynapseError=_e("instance", "synapse"),
        ),
        SchematicError=_e("schematic", ConstructionError=_e(), FrozenError=_e()),
    ),
)

ArborizeError: type[Exception]
ModelDefinitionError: type["ArborizeError"]  # noqa: F821
ModelError: type["ArborizeError"]  # noqa: F821
TransmitterError: type["ModelError"]  # noqa: F821
UnknownLocationError: type["ModelError"]  # noqa: F821
UnknownSynapseError: type["ModelError"]  # noqa: F821
SchematicError: type["ArborizeError"]  # noqa: F821
ConstructionError: type["SchematicError"]  # noqa: F821
FrozenError: type["SchematicError"]  # noqa: F821
