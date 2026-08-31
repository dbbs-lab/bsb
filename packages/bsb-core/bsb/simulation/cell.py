import typing

from .. import config
from ..config import refs
from ..config._attrs import cfgdict
from .component import SimulationComponent
from .parameter import CellParameter, parameter

if typing.TYPE_CHECKING:  # pragma: nocover
    from ..cell_types import CellType


@config.node
class CellModel(SimulationComponent):
    """
    Cell models are simulator specific representations of a cell type.
    """

    cell_type: "CellType" = config.ref(refs.cell_type_ref, key="name")
    """
    The cell type that this model represents.
    """
    parameters: cfgdict[str, CellParameter] = config.dict(type=parameter(CellParameter))
    """
    Parameters of the model, computed once per cell when the simulation is loaded.

    Keyed by the model parameter they set. A bare value is a constant; a node with a
    ``strategy`` selects a :class:`~bsb.simulation.parameter.CellParameter`.
    """

    def __lt__(self, other):
        try:
            return self.name < other.name
        except Exception:
            return True

    def get_placement_set(self, chunks=None):
        return self.cell_type.get_placement_set(chunks=chunks)


__all__ = ["CellModel"]
