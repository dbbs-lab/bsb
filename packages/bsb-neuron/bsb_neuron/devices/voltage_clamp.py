import warnings

from bsb import LocationTargetting, config, point_annotations, types

from .._util import ignore_arborize_proxy_warnings
from ..device import NeuronDevice


@config.node
class VoltageClamp(NeuronDevice, classmap_entry="vclamp"):
    locations = config.attr(type=LocationTargetting, default={"strategy": "soma"})
    """Location of the voltage clamp on the section"""
    voltage = config.attr(
        type=types.or_(float, types.list(type=float, size=3)), required=True
    )
    """Voltage value during the step or three values for before, during and after 
    the step"""
    before = config.attr(type=float, default=None)
    """Delay before the voltage step"""
    duration = config.attr(type=float, default=None)
    """Duration of the voltage step"""
    after = config.attr(type=float, default=None)
    """Hold duration after voltage step"""
    holding = config.attr(type=float, default=None)
    """Voltage value in the `before` and `after` delays"""

    def implement(self, adapter, simulation, simdata):
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                clamped = False
                for location in self.locations.get_locations(target):
                    if clamped:
                        warnings.warn(
                            f"Multiple voltage clamps placed on {target}",
                            stacklevel=2,
                        )
                    self._add_clamp(simdata.result, target, location)
                    clamped = True

    @ignore_arborize_proxy_warnings()
    def _add_clamp(self, results, target, location):
        sx = location.arc(0.5)
        clamp = location.section.vclamp(
            voltage=self.voltage,
            x=sx,
            **{
                k: v
                for k in ["before", "duration", "after", "holding"]
                if (v := getattr(self, k)) is not None
            },
        )
        # The clamp records the current it injects to hold the voltage.
        results.record(
            clamp._ref_i,
            device=self,
            name="i",
            units="nA",
            **point_annotations(
                target.cell_model, target.id, *location._loc, sx, "stimulate"
            ),
        )
