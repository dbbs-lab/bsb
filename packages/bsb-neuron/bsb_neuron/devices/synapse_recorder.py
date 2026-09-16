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
        targets = {
            id(target): target
            for pop in self.targetting.get_targets(adapter, simulation, simdata).values()
            for target in pop
        }
        # The sections the targeted locations are on. Locations on the same section
        # share its synapses, so each synapse is recorded once however many of the
        # targeted locations hold it.
        sections = {
            id(location.section)
            for target in targets.values()
            for location in self.locations.get_locations(target)
        }
        # The synapses of a section were appended in the order the connection models
        # made their receivers, so walking the receivers again, in that order, pairs
        # each synapse with its connection without anything kept on the synapse.
        inserted = {}
        for conn_model in simulation.connection_models.values():
            if not hasattr(conn_model, "iter_receivers"):
                continue
            cs = simulation.scaffold.get_connectivity_set(conn_model.name)
            for receiver in conn_model.iter_receivers(simdata, cs):
                location = receiver.cell.get_location(receiver.location)
                section = location.section
                index = inserted.get(id(section), 0)
                inserted[id(section)] = index + 1
                if id(receiver.cell) not in targets or id(section) not in sections:
                    continue
                synapse = section.synapses[index]
                if self.synapse_types and synapse.synapse_name not in self.synapse_types:
                    continue
                self._record_synaptic_current(simdata.result, receiver, location, synapse)

    def _record_synaptic_current(self, result, receiver, location, synapse):
        pre_id, pre_branch, pre_point = receiver.pre
        result.record(
            synapse._pp._ref_i,
            device=self,
            name="i",
            units="nA",
            target=synapse_annotations(
                (
                    receiver.cell.cell_model,
                    receiver.cell.id,
                    *receiver.location,
                    location.arc(0.5),
                ),
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
