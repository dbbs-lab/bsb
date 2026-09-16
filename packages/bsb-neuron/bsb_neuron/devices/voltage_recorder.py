from bsb import LocationTargetting, config, point_annotations

from .._util import ignore_arborize_proxy_warnings
from ..device import NeuronDevice


@config.node
class VoltageRecorder(NeuronDevice, classmap_entry="voltage_recorder"):
    locations: LocationTargetting = config.attr(
        type=LocationTargetting, default={"strategy": "soma"}
    )
    """Device to record membrane voltage from specified neuron locations."""

    def implement(self, adapter, simulation, simdata):
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                for location in self.locations.get_locations(target):
                    self._add_voltage_recorder(simdata.result, target, location)

    @ignore_arborize_proxy_warnings()
    def _add_voltage_recorder(self, results, target, location):
        section = location.section
        x = location.arc(0)
        results.record(
            section(x)._ref_v,
            device=self,
            name="v",
            **point_annotations(
                target.cell_model, target.id, *location._loc, x, "record"
            ),
        )
