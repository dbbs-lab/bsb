import nest
import numpy as np
from bsb import config
from neo import SpikeTrain

from ..device import NestDevice


@config.node
class SpikeRecorder(NestDevice, classmap_entry="spike_recorder"):
    weight = config.provide(1)

    def implement(self, adapter, simulation, simdata):
        nodes = self.get_target_nodes(adapter, simulation, simdata)
        device = self.register_device(simdata, nest.Create("spike_recorder"))
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            global_ids = simdata.get_bsb_ids(device.events["senders"])
            ps_names = [g[0] for g in global_ids]
            ps_names, ps_ids = np.unique(ps_names, return_inverse=True)
            segment.spiketrains.append(
                SpikeTrain(
                    device.events["times"],
                    units="ms",
                    array_annotations={
                        "senders": [g[1] for g in global_ids],
                        "ps_ids": ps_ids,
                    },
                    t_stop=simulation.duration,
                    device=self.name,
                    pop_size=len(nodes),
                    ps_names=ps_names,
                )
            )

        simdata.result.create_recorder(recorder)
