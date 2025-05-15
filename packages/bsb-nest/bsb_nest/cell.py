import nest
from bsb import CellModel, config

from .distributions import NestRandomDistribution, nest_parameter


@config.node
class NestCell(CellModel):
    model = config.attr(type=str, default="iaf_psc_alpha")
    """Importable reference to the NEST model describing the cell type."""
    constants = config.dict(type=nest_parameter())
    """Dictionary of the constants values to assign to the cell model."""

    def create_population(self, simdata):
        n = len(simdata.placement[self])
        population = nest.Create(self.model, n) if n else nest.NodeCollection([])
        self.set_constants(population)
        self.set_parameters(population, simdata)
        return population

    def set_constants(self, population):
        population.set(
            {
                k: (v() if isinstance(v, NestRandomDistribution) else v)
                for k, v in self.constants.items()
            }
        )

    def set_parameters(self, population, simdata):
        ps = simdata.placement[self]
        for param in self.parameters:
            population.set(param.name, param.get_value(ps))
