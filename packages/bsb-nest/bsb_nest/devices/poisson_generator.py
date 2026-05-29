import nest
import numpy as np
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
        sr = nest.Create("spike_recorder")
        nest.Connect(device, sr)
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            # Stimulator: it does not record cells in the BSB model, only its
            # own emitted spikes, so the train carries no (ps_name, cell_id).
            segment.spiketrains.append(
                simdata.result.stimulus_train(
                    times=np.asarray(sr.events["times"]),
                    device=self,
                    target_count=len(nodes),
                    t_stop=simulation.duration,
                )
            )

        simdata.result.create_recorder(recorder, device=self)
