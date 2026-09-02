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
        targets = {}
        for model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            ps_name = model.cell_type.name
            for target in pop:
                targets.setdefault(ps_name, []).append(target.id)
                for location in self.locations.get_locations(target):
                    for synapse in location.section.synapses:
                        if (
                            not self.synapse_types
                            or synapse.synapse_name in self.synapse_types
                        ):
                            _record_synaptic_current(
                                simdata.result,
                                synapse,
                                device=self,
                                location=location,
                                ps_name=ps_name,
                                cell_id=target.id,
                                cell_model=target.cell_model.name,
                                synapse_type=synapse.synapse_name,
                            )
        simdata.result.record_device_targets(self, targets)


def _record_synaptic_current(result, synapse, *, location, **annotations):
    # A `synapse` recording kind, which would carry the presynaptic identity too,
    # waits for the LFP work in #50. Until then this is the point the synapse sits
    # on, which is true and already addressable.
    result.record(
        synapse._pp._ref_i,
        name="i",
        units="nA",
        recording_kind="point",
        branch=int(location.location[0]),
        point=int(location.location[1]),
        arc=float(location.arc(0)),
        **annotations,
    )
