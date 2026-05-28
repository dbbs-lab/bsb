import nest
from bsb import CellModel, ConfigurationError, TypeHandler, config, warn

from ._kernel_proxy import get_nest_kernel_proxy, load_simulation_modules
from .distributions import NestRandomDistribution, nest_parameter
from .exceptions import KernelWarning


class nest_node_model(TypeHandler):
    """Validate a NEST node (cell) model name against the build's NEST kernel.

    Queries the out-of-process kernel proxy, so loading a configuration never
    imports ``nest`` in-process. An unknown model is a hard
    :class:`~bsb.exceptions.ConfigurationError` when the kernel is reachable;
    when it can't be reached the name passes through and the real error
    surfaces later at ``nest.Create`` time.
    """

    def __call__(self, value, _key=None, _parent=None):
        value = str(value)
        try:
            proxy = get_nest_kernel_proxy()
            if proxy is None:
                return value
            load_simulation_modules(_parent, proxy)
            node_models = proxy.models(mtype="nodes")
        except ConfigurationError:
            raise
        except Exception as e:
            warn(f"Could not validate cell model '{value}': {e}", KernelWarning)
            return value
        if value not in node_models:
            raise ConfigurationError(f"Unknown cell model '{value}'.")
        return value

    @property
    def __name__(self):  # pragma: nocover
        return "nest node model"

    def __inv__(self, value):
        return value


@config.node
class NestCell(CellModel):
    model = config.attr(type=nest_node_model(), default="iaf_psc_alpha")
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
