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
            segment.spiketrains.append(
                SpikeTrain(
                    device.events["times"],
                    units="ms",
                    array_annotations={"senders": device.events["senders"]},
                    t_stop=simulation.duration,
                    device=self.name,
                    pop_size=len(nodes),
                )
            )

        simdata.result.create_recorder(recorder)
