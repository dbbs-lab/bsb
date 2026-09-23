import nest
import numpy as np
from bsb import cell_annotations, config, multiplex_targets
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
        # Each rank writes the spikes of the targets it hosts, and the ranks' results
        # are concatenated: a rank writing every target would repeat each cell once
        # per rank. Kept as a NEST collection, which does not hold a node id per node.
        local_nodes = nest.GetLocalNodeCollection(nodes) if len(nodes) else None

        def recorder(segment):
            local_node_ids = local_nodes.tolist() if local_nodes is not None else []
            if not local_node_ids:
                return
            # One roster entry per cell the device watches, silent ones included.
            # Which cells those were is then the roster itself, so nothing has to say
            # it a second time, and a silent cell is told apart from one that was
            # never watched by reading the results alone.
            targets = [
                cell_annotations(*self._cell_of_node(ranges, node), "record")
                for node in local_node_ids
            ]
            senders = np.asarray(device.events["senders"])
            times = np.asarray(device.events["times"])
            # Senders are keyed on node ids, which is what the recorder reports; the
            # roster names the cell, never the node, so spikes are mapped from node id
            # to roster position before anything is written.
            sorted_nodes = np.asarray(local_node_ids)
            order = np.argsort(sorted_nodes)
            sorted_nodes = sorted_nodes[order]
            mask = np.isin(senders, sorted_nodes)
            target_index = order[np.searchsorted(sorted_nodes, senders[mask])]
            segment.spiketrains.append(
                SpikeTrain(
                    times[mask],
                    units="ms",
                    t_stop=simulation.duration,
                    name="spikes",
                    array_annotations={"bsb_target_index": target_index},
                    **multiplex_targets(targets),
                )
            )

        simdata.result.create_recorder(recorder, device=self)
