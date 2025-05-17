from bsb import LocationTargetting, config

from ..device import NeuronDevice


@config.node
class VoltageRecorder(NeuronDevice, classmap_entry="voltage_recorder"):
    locations = config.attr(type=LocationTargetting, default={"strategy": "soma"})

    def implement(self, adapter, simulation, simdata):
        for model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                for location in self.locations.get_locations(target):
                    self._add_voltage_recorder(
                        simdata.result,
                        location,
                        name=self.name,
                        cell_type=target.cell_model.name,
                        cell_id=target.id,
                    )

    def _add_voltage_recorder(self, results, location, **annotations):
        section = location.section
        x = location.arc(0)
        results.record(section(x)._ref_v, **annotations)
