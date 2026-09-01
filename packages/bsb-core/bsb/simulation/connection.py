from .. import config
from ..config._attrs import cfgdict
from .component import SimulationComponent
from .parameter import ConnectionParameter, parameter


@config.node
class ConnectionModel(SimulationComponent):
    tag: str = config.attr(type=str, key=True)

    parameters: cfgdict[str, ConnectionParameter] = config.dict(
        type=parameter(ConnectionParameter)
    )
    """
    Parameters of the model, computed once per connection when the simulation is
    loaded.

    Keyed by the model parameter they set. A bare value is a constant; a node with a
    ``strategy`` selects a
    :class:`~bsb.simulation.parameter.ConnectionParameter`.
    """

    def get_connectivity_set(self):
        return self.scaffold.get_connectivity_set(self.tag)


__all__ = ["ConnectionModel"]
