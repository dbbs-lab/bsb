import warnings

from bsb import LocationTargetting, config, types

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
        for target in self.targetting.get_targets(adapter, simulation, simdata):
            clamped = False
            for location in self.locations.get_locations(target):
                if clamped:
                    warnings.warn(
                        f"Multiple voltage clamps placed on {target}",
                        stacklevel=2,
                    )
                self._add_clamp(
                    simdata.results,
                    location,
                    name=self.name,
                    cell_type=target.cell_model.name,
                    cell_id=target.id,
                )
                clamped = True

    def _add_clamp(self, results, location, **annotations):
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
        results.record(clamp, **annotations)
