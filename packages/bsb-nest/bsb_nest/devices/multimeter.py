import nest
import numpy as np
import quantities as pq
from bsb import ConfigurationError, _util, config, types
from neo import AnalogSignal

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
        inv_targets = self._invert_targets_dict(targets_dict)
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
            senders = device.events["senders"]
            u_sender = np.unique(senders)
            global_ids, tags = self.get_bsb_ids(u_sender, simulation, simdata)
            for sender, global_id in zip(u_sender, global_ids, strict=True):
                sender_filter = senders == sender
                for prop, unit in zip(self.properties, self.units, strict=False):
                    segment.analogsignals.append(
                        AnalogSignal(
                            device.events[prop][sender_filter],
                            units=pq.units.__dict__[unit],
                            sampling_period=self.simulation.resolution * pq.ms,
                            name=self.name,
                            cell_type=inv_targets[sender],
                            cell_id=global_id[1],
                            ps_name=tags[global_id[0]],
                            prop_recorded=prop,
                        )
                    )

        simdata.result.create_recorder(recorder)
