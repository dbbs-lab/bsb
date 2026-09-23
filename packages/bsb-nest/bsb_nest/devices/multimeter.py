import nest
import numpy as np
import quantities as pq
from bsb import (
    ConfigurationError,
    _util,
    cell_annotations,
    config,
    multiplex_channels,
    types,
)
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
        ranges = self._node_ranges(simdata, targets_dict)
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
            unique_senders = np.unique(senders)
            if not len(unique_senders):
                return
            # One channel per cell this rank recorded, in the same order for every
            # property, so all of a checkpoint's properties multiplex the same roster.
            targets = [
                cell_annotations(*self._cell_of_node(ranges, int(sender)), "record")
                for sender in unique_senders
            ]
            baseline, array_annotations = multiplex_channels(targets)
            for prop, unit in zip(self.properties, self.units, strict=False):
                data = np.stack(
                    [device.events[prop][senders == sender] for sender in unique_senders],
                    axis=1,
                )
                segment.analogsignals.append(
                    AnalogSignal(
                        data,
                        units=pq.units.__dict__[unit],
                        sampling_period=self.simulation.resolution * pq.ms,
                        name=prop,
                        array_annotations=array_annotations,
                        **baseline,
                    )
                )

        simdata.result.create_recorder(recorder, device=self)
