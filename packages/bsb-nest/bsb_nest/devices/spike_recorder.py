import nest
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
            global_ids, tags = self.get_bsb_ids(
                device.events["senders"], simulation, simdata
            )
            segment.spiketrains.append(
                SpikeTrain(
                    device.events["times"],
                    units="ms",
                    array_annotations={
                        "senders": global_ids[:, 1],
                        "ps_ids": global_ids[:, 0],
                    },
                    t_stop=simulation.duration,
                    device=self.name,
                    pop_size=len(nodes),
                    ps_names=tags,
                )
            )

        simdata.result.create_recorder(recorder)
