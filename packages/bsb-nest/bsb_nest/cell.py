import nest
from bsb import CellModel, CellParameter, ParameterizedModel, config

from ._kernel_proxy import NestModelTypeHandler
from .distributions import nest_constant, nest_parameter


class nest_node_model(NestModelTypeHandler):
    """Validate a NEST node (cell) model name against the build's kernel."""

    mtype = "nodes"
    kind = "cell"


@config.node
class NestCell(ParameterizedModel, CellModel):
    model = config.attr(type=nest_node_model(), default="iaf_psc_alpha")
    """Importable reference to the NEST model describing the cell type."""
    constants = config.dict(type=nest_constant())
    """
    Constant values to assign to the cell model.

    A bare value, or a ``distribution`` node NEST draws itself. A computed
    parameter belongs in :attr:`parameters`.
    """
    parameters = config.dict(type=nest_parameter(CellParameter))
    """
    Parameters of the cell model, resolved when the simulation loads.

    Accepts everything :attr:`constants` does, plus a ``strategy`` node selecting a
    :class:`~bsb.simulation.parameter.CellParameter` computed per cell.
    """

    def get_parameter_groups(self):
        return (self.constants, self.parameters)

    def create_population(self, simdata):
        n = len(simdata.placement[self])
        population = nest.Create(self.model, n) if n else nest.NodeCollection([])
        self.set_parameters(population, simdata)
        return population

    def set_parameters(self, population, simdata):
        # NEST assigns a whole mapping at once; setting them one by one would be a
        # kernel round trip per parameter.
        ps = simdata.placement[self]
        population.set(self.compute_parameters(self.simulation, ps))
