from bsb import LocationTargetting, config

from .._util import ignore_arborize_proxy_warnings
from ..device import NeuronDevice


@config.node
class SynapseRecorder(NeuronDevice, classmap_entry="synapse_recorder"):
    locations = config.attr(type=LocationTargetting, required=True)
    """Location of the synapse recorder on the section"""
    synapse_types = config.list()
    """List of synaptic types"""

    @ignore_arborize_proxy_warnings()
    def implement(self, adapter, simulation, simdata):
        for cell_model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = simdata.placement[cell_model].cell_type.name
            for target in pop:
                for location in self.locations.get_locations(target):
                    for synapse in location.section.synapses:
                        if (
                            not self.synapse_types
                            or synapse.synapse_name in self.synapse_types
                        ):
                            self._record_synaptic_current(
                                simulation,
                                simdata,
                                synapse,
                                location,
                                cell_model=cell_model,
                                ps_name=ps_name,
                                cell_id=target.id,
                            )

    def _record_synaptic_current(
        self, simulation, simdata, synapse, location, *, cell_model, ps_name, cell_id
    ):
        from patch import p
        from quantities import ms, nA

        vec = p.record(synapse._pp._ref_i)
        branch, point = location.location
        arc = float(location.arc(0))

        def flush(segment):
            segment.analogsignals.append(
                simdata.result.analog_signal(
                    data=list(vec),
                    units=nA,
                    sampling_period=p.dt * ms,
                    name="I_syn",
                    target_kind="synapse",
                    ps_name=ps_name,
                    cell_id=cell_id,
                    cell_model=cell_model,
                    device=self,
                    branch=branch,
                    point=point,
                    arc=arc,
                    synapse_type=synapse.synapse_name,
                )
            )
            if vec.size():
                vec.remove(0, vec.size() - 1)

        simdata.result.create_recorder(flush)
