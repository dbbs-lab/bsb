from .. import config
from .._util import obj_str_insert


@config.node
class SimulationComponent:
    name: str = config.attr(key=True)

    @property
    def simulation(self):
        return self._config_parent._config_parent

    @obj_str_insert
    def __str__(self):
        return f"'{self.name}'"

    def implement(self, adapter, simulation, simdata):
        """Method that gives each component the opportunity to store the context they need to operate"""
        pass


__all__ = ["SimulationComponent"]
