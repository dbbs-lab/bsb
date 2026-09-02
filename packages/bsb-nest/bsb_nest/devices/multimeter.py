import nest
import numpy as np
import quantities as pq
from bsb import ConfigurationError, _util, config, types

from ..device import NestDevice


@config.node
class Multimeter(NestDevice, classmap_entry="multimeter"):
    weight = config.provide(1)
    properties: list[str] = config.attr(type=types.list(str))
    """List of properties to record in the Nest model."""
    units: list[str] = config.attr(type=types.list(str))
    """List of properties' units."""

    def boot(self):
        _util.assert_samelen(self.properties, self.units)
        for i in range(len(self.units)):
            if self.units[i] not in pq.units.__dict__:
                raise ConfigurationError(
                    f"Unit {self.units[i]} not in the list of known units of quantities"
                )

    def implement(self, adapter, simulation, simdata):
        targets_dict = self.get_dict_targets(adapter, simulation, simdata)
        nodes = self._flatten_nodes_ids(targets_dict)
        # NEST id -> the cell it stands for. NEST's own ids do not leave the adapter.
        lookup = {}
        targets = {}
        for cell_model, collection in targets_dict.items():
            ps_name = simdata.placement[cell_model].cell_type.name
            ids = collection.tolist()
            for cell_id, sim_id in enumerate(ids):
                lookup[int(sim_id)] = (cell_model, ps_name, cell_id)
            targets.setdefault(ps_name, []).extend(range(len(ids)))
        simdata.result.record_device_targets(self, targets)
        device = self.register_device(
            simdata,
            nest.Create(
                "multimeter",
                params={
                    "interval": self.simulation.resolution,
                    "record_from": self.properties,
                },
            ),
        )
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            for sender in np.unique(senders):
                entry = lookup.get(int(sender))
                if entry is None:
                    continue
                cell_model, ps_name, cell_id = entry
                sender_filter = senders == sender
                for prop, unit in zip(self.properties, self.units, strict=False):
                    segment.analogsignals.append(
                        simdata.result.analog_signal(
                            data=device.events[prop][sender_filter],
                            units=pq.units.__dict__[unit],
                            sampling_period=self.simulation.resolution * pq.ms,
                            name=prop,
                            ps_name=ps_name,
                            cell_id=cell_id,
                            cell_model=cell_model,
                            device=self,
                        )
                    )

        simdata.result.create_recorder(recorder, device=self)
