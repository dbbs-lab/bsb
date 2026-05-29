import nest
import numpy as np
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
            # Stimulator: it does not record cells in the BSB model, only its
            # own emitted spikes. We expose them on a SpikeTrain that doesn't
            # carry a (ps_name, cell_id) — the bsb_* annotations identify it
            # as a stimulator output. This is intentional and outside the
            # ``iter_recordings`` convention (which filters on bsb_ps_name).
            segment.spiketrains.append(
                SpikeTrain(
                    np.asarray(sr.events["times"]),
                    units="ms",
                    t_stop=simulation.duration,
                    bsb_device_name=self.name,
                    bsb_device_kind=self.__class__.classmap_entry,
                    bsb_target_kind="stimulus",
                    bsb_simulation_id=simdata.result.simulation_id,
                    bsb_segment_id=simdata.result.segment_id,
                    bsb_target_count=len(nodes),
                )
            )

        simdata.result.create_recorder(recorder, device=self)
