from bsb import LocationTargetting, config, warn

from ..device import NeuronDevice


@config.node
class CurrentClamp(NeuronDevice, classmap_entry="current_clamp"):
    locations = config.attr(type=LocationTargetting, default={"strategy": "soma"})
    """Location of the current clamp on the section"""
    amplitude = config.attr(type=float, required=True)
    """Current amplitude"""
    before = config.attr(type=float, default=None)
    """Delay before current get injected"""
    duration = config.attr(type=float, default=None)
    """Duration of the current step"""

    def implement(self, adapter, simulation, simdata):
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                clamped = False
                for location in self.locations.get_locations(target):
                    if clamped:
                        warn(f"Multiple current clamps placed on {target}")
                    self._add_clamp(
                        simdata,
                        location,
                        name=self.name,
                        cell_type=target.cell_model.name,
                        cell_id=target.id,
                    )
                    clamped = True

    def _add_clamp(self, simdata, location, **annotations):
        sx = location.arc(0.5)
        clamp = location.section.iclamp(
            x=sx, delay=self.before, duration=self.duration, amplitude=self.amplitude
        )
        simdata.result.record(clamp._ref_i, **annotations, units="nA")
