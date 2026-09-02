import nest
import numpy as np
from bsb import config
from neo import SpikeTrain

from ..device import NestDevice


@config.node
class SpikeRecorder(NestDevice, classmap_entry="spike_recorder"):
    weight = config.provide(1)

    def implement(self, adapter, simulation, simdata):
        targets_dict = self.get_dict_targets(adapter, simulation, simdata)
        nodes = self._flatten_nodes_ids(targets_dict)
        inv_targets = self._invert_targets_dict(targets_dict)
        device = self.register_device(simdata, nest.Create("spike_recorder"))
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            times = np.asarray(device.events["times"])
            # One train per cell that spiked. A cell that stayed silent writes
            # nothing: absence from the results is what silence looks like, and
            # the device's targets say which cells could have been there.
            for sender in np.unique(senders):
                segment.spiketrains.append(
                    SpikeTrain(
                        times[senders == sender],
                        units="ms",
                        t_stop=simulation.duration,
                        name=self.name,
                        cell_id=int(sender),
                        cell_type=inv_targets[sender],
                        pop_size=len(nodes),
                    )
                )

        simdata.result.create_recorder(recorder, device=self)
