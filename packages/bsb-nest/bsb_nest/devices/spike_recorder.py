import nest
import numpy as np
from bsb import cell_annotations, config
from neo import SpikeTrain

from ..device import NestDevice


@config.node
class SpikeRecorder(NestDevice, classmap_entry="spike_recorder"):
    weight = config.provide(1)

    def implement(self, adapter, simulation, simdata):
        targets_dict = self.get_dict_targets(adapter, simulation, simdata)
        nodes = self._flatten_nodes_ids(targets_dict)
        ranges = self._node_ranges(simdata, targets_dict)
        device = self.register_device(simdata, nest.Create("spike_recorder"))
        self.connect_to_nodes(device, nodes)
        # Each rank writes the trains of the targets it hosts, and the ranks' results
        # are concatenated: a rank writing every target would repeat each cell once
        # per rank. Kept as a NEST collection, which does not hold a node id per node.
        local_nodes = nest.GetLocalNodeCollection(nodes) if len(nodes) else None

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            times = np.asarray(device.events["times"])
            # One train per cell the device watched, empty ones included. Which
            # cells those were is then the set of recordings itself, so nothing
            # has to say it a second time, and a silent cell is told apart from
            # one that was never watched by reading the results alone.
            # Trains are keyed on node ids, which is what the recorder reports its
            # senders by. The train itself names the cell, never the node.
            for node in local_nodes.tolist() if local_nodes is not None else ():
                cell_model, cell_id = self._cell_of_node(ranges, node)
                segment.spiketrains.append(
                    SpikeTrain(
                        times[senders == node],
                        units="ms",
                        t_stop=simulation.duration,
                        name="spikes",
                        **cell_annotations(cell_model, cell_id, "record"),
                    )
                )

        simdata.result.create_recorder(recorder, device=self)
