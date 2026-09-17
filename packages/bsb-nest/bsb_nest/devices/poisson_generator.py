import nest
from bsb import config

from ..device import NestDevice


@config.node
class PoissonGenerator(NestDevice, classmap_entry="poisson_generator"):
    rate = config.attr(type=float, required=True)
    """Frequency of the poisson generator"""
    start = config.attr(type=float, required=False, default=0.0)
    """Activation time in ms"""
    stop = config.attr(type=float, required=False, default=None)
    """Deactivation time in ms.
        If not specified, generator will last until the end of the simulation."""

    def implement(self, adapter, simulation, simdata):
        nodes = self.get_target_nodes(adapter, simulation, simdata)
        params = {"rate": self.rate, "start": self.start}
        if self.stop is not None and self.stop > self.start:
            params["stop"] = self.stop
        device = self.register_device(
            simdata, nest.Create("poisson_generator", params=params)
        )
        self.connect_to_nodes(device, nodes)
