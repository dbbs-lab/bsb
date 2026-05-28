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
        for cell_model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = simdata.placement[cell_model].cell_type.name
            for target in pop:
                clamped = False
                for location in self.locations.get_locations(target):
                    if clamped:
                        warn(f"Multiple current clamps placed on {target}")
                    self._add_clamp(
                        simulation,
                        simdata,
                        location,
                        cell_model=cell_model,
                        ps_name=ps_name,
                        cell_id=target.id,
                    )
                    clamped = True

    @ignore_arborize_proxy_warnings()
    def _add_clamp(
        self, simulation, simdata, location, *, cell_model, ps_name, cell_id
    ):
        from patch import p
        from quantities import ms, nA

        sx = location.arc(0.5)
        section = location.section
        clamp = section.iclamp(
            x=sx, delay=self.before, duration=self.duration, amplitude=self.amplitude
        )
        vec = p.record(clamp._ref_i)
        loc = {
            "section": getattr(section, "name", str(section)),
            "x": float(sx),
            "compartment_index": getattr(location, "compartment_index", None),
        }

        def flush(segment):
            segment.analogsignals.append(
                simdata.result.analog_signal(
                    data=list(vec),
                    units=nA,
                    sampling_period=p.dt * ms,
                    name="I_clamp",
                    ps_name=ps_name,
                    cell_id=cell_id,
                    cell_model=cell_model,
                    device=self,
                    location=loc,
                )
            )
            if vec.size():
                vec.remove(0, vec.size() - 1)

        simdata.result.create_recorder(flush)
