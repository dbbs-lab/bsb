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
        for cell_model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = simdata.placement[cell_model].cell_type.name
            for target in pop:
                for location in self.locations.get_locations(target):
                    self._add_voltage_recorder(
                        simulation,
                        simdata,
                        location,
                        cell_model=cell_model,
                        ps_name=ps_name,
                        cell_id=target.id,
                    )

    @ignore_arborize_proxy_warnings()
    def _add_voltage_recorder(
        self, simulation, simdata, location, *, cell_model, ps_name, cell_id
    ):
        from patch import p
        from quantities import ms, mV

        section = location.section
        x = location.arc(0)
        vec = p.record(section(x)._ref_v)
        branch, point = location.location

        def flush(segment):
            segment.analogsignals.append(
                simdata.result.analog_signal(
                    data=list(vec),
                    units=mV,
                    sampling_period=p.dt * ms,
                    name="V_m",
                    target_kind="compartment",
                    ps_name=ps_name,
                    cell_id=cell_id,
                    cell_model=cell_model,
                    device=self,
                    branch=branch,
                    point=point,
                    arc=float(x),
                )
            )
            if vec.size():
                vec.remove(0, vec.size() - 1)

        simdata.result.create_recorder(flush)
