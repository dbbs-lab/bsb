from bsb import LocationTargetting, config, synapse_annotations, warn

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
        receiver = getattr(synapse, "receiver", None)
        if receiver is None:
            warn(
                f"Device '{self.name}' cannot record a '{synapse.synapse_name}' synapse "
                f"of cell {target.id}: it was not made by a connection, so where it is "
                "and what it connects is unknown."
            )
            return
        pre_id, pre_branch, pre_point = receiver.pre
        location = target.get_location(receiver.location)
        result.record(
            synapse._pp._ref_i,
            device=self,
            name="i",
            units="nA",
            target=synapse_annotations(
                (target.cell_model, target.id, *receiver.location, location.arc(0.5)),
                synapse.synapse_name,
                "record",
                pre=(
                    None
                    if receiver.pre_model is None
                    else (receiver.pre_model, pre_id, pre_branch, pre_point)
                ),
                connectivity_set=receiver.connectivity_set,
            ),
        )
