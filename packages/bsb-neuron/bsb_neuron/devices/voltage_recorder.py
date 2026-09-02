from bsb import LocationTargetting, config

from .._util import ignore_arborize_proxy_warnings
from ..device import NeuronDevice


@config.node
class VoltageRecorder(NeuronDevice, classmap_entry="voltage_recorder"):
    locations: LocationTargetting = config.attr(
        type=LocationTargetting, default={"strategy": "soma"}
    )
    """Device to record membrane voltage from specified neuron locations."""

    def implement(self, adapter, simulation, simdata):
        targets = {}
        for model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = model.cell_type.name
            for target in pop:
                targets.setdefault(ps_name, []).append(target.id)
                for location in self.locations.get_locations(target):
                    self._add_voltage_recorder(
                        simdata.result,
                        location,
                        ps_name=ps_name,
                        cell_id=target.id,
                        cell_model=target.cell_model.name,
                    )
        simdata.result.record_device_targets(self, targets)

    @ignore_arborize_proxy_warnings()
    def _add_voltage_recorder(self, results, location, **annotations):
        section = location.section
        x = location.arc(0)
        results.record(
            section(x)._ref_v,
            device=self,
            name="v",
            # Addressed the way BSB addresses a morphology everywhere else. How
            # NEURON discretises one is its own business and stays in this adapter.
            recording_kind="point",
            branch=int(location.location[0]),
            point=int(location.location[1]),
            arc=float(x),
            **annotations,
        )
