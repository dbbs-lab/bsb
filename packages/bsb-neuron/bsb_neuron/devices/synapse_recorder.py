from bsb import LocationTargetting, config, synapse_annotations

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
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                # Locations on the same section share its synapses, so each synapse
                # is recorded once however many of the targeted locations hold it.
                synapses = {
                    id(synapse): synapse
                    for location in self.locations.get_locations(target)
                    for synapse in location.section.synapses
                    if not self.synapse_types
                    or synapse.synapse_name in self.synapse_types
                }
                for synapse in synapses.values():
                    self._record_synaptic_current(simdata.result, target, synapse)

    def _record_synaptic_current(self, result, target, synapse):
        branch, point = synapse.bsb_location
        result.record(
            synapse._pp._ref_i,
            device=self,
            name="i",
            units="nA",
            target=synapse_annotations(
                target.cell_model,
                target.id,
                branch,
                point,
                synapse.bsb_arc,
                synapse.synapse_name,
                "record",
                presynaptic=getattr(synapse, "bsb_presynaptic", None),
            ),
        )
