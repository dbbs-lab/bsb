import nest
import numpy as np
from bsb import config

from ..device import NestDevice


@config.node
class SpikeRecorder(NestDevice, classmap_entry="spike_recorder"):
    weight = config.provide(1)

    def implement(self, adapter, simulation, simdata):
        targets_dict = self.get_dict_targets(adapter, simulation, simdata)
        nodes = self._flatten_nodes_ids(targets_dict)
        device = self.register_device(simdata, nest.Create("spike_recorder"))
        self.connect_to_nodes(device, nodes)

        # NEST node id -> (cell_model, ps_name, cell_id_within_ps), captured at
        # prepare time so flush() doesn't need to re-walk the NodeCollections.
        # BSB itself does not use GIDs; this mapping is local to the adapter.
        lookup = _build_lookup(simdata, targets_dict)

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            times = np.asarray(device.events["times"])
            for sim_id in np.unique(senders):
                entry = lookup.get(int(sim_id))
                if entry is None:
                    continue
                cell_model, ps_name, cell_id = entry
                mask = senders == sim_id
                segment.spiketrains.append(
                    simdata.result.spike_train(
                        times=times[mask],
                        ps_name=ps_name,
                        cell_id=cell_id,
                        cell_model=cell_model,
                        device=self,
                        t_stop=simulation.duration,
                    )
                )

        simdata.result.create_recorder(recorder, device=self)


def _build_lookup(simdata, targets_dict):
    lookup = {}
    for cell_model, nc in targets_dict.items():
        ps = simdata.placement[cell_model]
        ps_name = ps.cell_type.name
        for cell_id, sim_id in enumerate(nc.tolist()):
            lookup[int(sim_id)] = (cell_model, ps_name, cell_id)
    return lookup
