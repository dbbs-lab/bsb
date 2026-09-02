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

        # NEST id -> the cell it stands for, taken once at prepare time so a flush
        # does not have to walk the node collections again. BSB does not use NEST's
        # ids for anything else; they do not leave this adapter.
        lookup = _build_lookup(simdata, targets_dict)
        simdata.result.record_device_targets(
            self, _targets_by_set(simdata, targets_dict)
        )

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            times = np.asarray(device.events["times"])
            # Driven by what was recorded, not by what was targeted: a cell that
            # stayed silent leaves no object behind, and is recovered as a target
            # that produced no recording.
            for sender in np.unique(senders):
                entry = lookup.get(int(sender))
                if entry is None:
                    continue
                cell_model, ps_name, cell_id = entry
                segment.spiketrains.append(
                    simdata.result.spike_train(
                        times=times[senders == sender],
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
    for cell_model, collection in targets_dict.items():
        ps_name = simdata.placement[cell_model].cell_type.name
        for cell_id, sim_id in enumerate(collection.tolist()):
            lookup[int(sim_id)] = (cell_model, ps_name, cell_id)
    return lookup


def _targets_by_set(simdata, targets_dict):
    targets = {}
    for cell_model, collection in targets_dict.items():
        ps_name = simdata.placement[cell_model].cell_type.name
        targets.setdefault(ps_name, []).extend(range(len(collection.tolist())))
    return targets
