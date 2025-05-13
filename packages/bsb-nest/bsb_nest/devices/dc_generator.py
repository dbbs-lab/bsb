import nest
from bsb import config

from ..device import NestDevice


@config.node
class DCGenerator(NestDevice, classmap_entry="dc_generator"):
    amplitude = config.attr(type=float, required=True)
    """Current amplitude of the dc generator"""
    start = config.attr(type=float, required=False, default=0.0)
    """Activation time in ms"""
    stop = config.attr(type=float, required=False, default=None)
    """Deactivation time in ms. 
        If not specified, generator will last until the end of the simulation."""

    def implement(self, adapter, simulation, simdata):
        nodes = self.get_target_nodes(adapter, simulation, simdata)
        params = {"amplitude": self.amplitude, "start": self.start}
        if self.stop is not None and self.stop > self.start:
            params["stop"] = self.stop
        device = self.register_device(simdata, nest.Create("dc_generator", params=params))
        self.connect_to_nodes(device, nodes)
