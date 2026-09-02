from bsb import LocationTargetting, config, warn

from .._util import ignore_arborize_proxy_warnings
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
        targets = {}
        for model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = model.cell_type.name
            for target in pop:
                clamped = False
                targets.setdefault(ps_name, []).append(target.id)
                for location in self.locations.get_locations(target):
                    if clamped:
                        warn(f"Multiple current clamps placed on {target}")
                    self._add_clamp(
                        simdata,
                        location,
                        ps_name=ps_name,
                        cell_id=target.id,
                        cell_model=target.cell_model.name,
                    )
                    clamped = True
        simdata.result.record_device_targets(self, targets)

    @ignore_arborize_proxy_warnings()
    def _add_clamp(self, simdata, location, **annotations):
        sx = location.arc(0.5)
        clamp = location.section.iclamp(
            x=sx, delay=self.before, duration=self.duration, amplitude=self.amplitude
        )
        simdata.result.record(
            clamp._ref_i,
            device=self,
            name="i",
            units="nA",
            # The clamp drives the cell rather than observing it, at a point of its
            # morphology.
            recording_kind="point",
            direction="stimulate",
            branch=int(location.location[0]),
            point=int(location.location[1]),
            arc=float(sx),
            **annotations,
        )
