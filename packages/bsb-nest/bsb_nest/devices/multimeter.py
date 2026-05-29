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
        # NEST node id -> (cell_model, ps_name, cell_id_within_ps).
        lookup = _build_lookup(simdata, targets_dict)

        def recorder(segment):
            senders = np.asarray(device.events["senders"])
            for sim_id in np.unique(senders):
                entry = lookup.get(int(sim_id))
                if entry is None:
                    continue
                cell_model, ps_name, cell_id = entry
                sender_mask = senders == sim_id
                for prop, unit in zip(self.properties, self.units, strict=False):
                    segment.analogsignals.append(
                        simdata.result.analog_signal(
                            data=device.events[prop][sender_mask],
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


def _build_lookup(simdata, targets_dict):
    lookup = {}
    for cell_model, nc in targets_dict.items():
        ps = simdata.placement[cell_model]
        ps_name = ps.cell_type.name
        for cell_id, sim_id in enumerate(nc.tolist()):
            lookup[int(sim_id)] = (cell_model, ps_name, cell_id)
    return lookup
