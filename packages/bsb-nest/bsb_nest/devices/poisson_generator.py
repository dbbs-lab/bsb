import nest
from bsb import config
from neo import SpikeTrain

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
        sr = nest.Create("spike_recorder")
        nest.Connect(device, sr)
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            segment.spiketrains.append(
                SpikeTrain(
                    sr.events["times"],
                    units="ms",
                    array_annotations={"senders": sr.events["senders"]},
                    t_stop=simulation.duration,
                    device=self.name,
                    pop_size=len(nodes),
                )
            )

        simdata.result.create_recorder(recorder)
