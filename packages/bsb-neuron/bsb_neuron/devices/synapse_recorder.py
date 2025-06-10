from bsb import LocationTargetting, config

from ..device import NeuronDevice


@config.node
class SynapseRecorder(NeuronDevice, classmap_entry="synapse_recorder"):
    locations = config.attr(type=LocationTargetting, required=True)
    """Location of the synapse recorder on the section"""
    synapse_types = config.list()
    """List of synaptic types"""

    def implement(self, adapter, simulation, simdata):
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                for location in self.locations.get_locations(target):
                    for synapse in location.section.synapses:
                        if (
                            not self.synapse_types
                            or synapse.synapse_name in self.synapse_types
                        ):
                            _record_synaptic_current(
                                simdata.result,
                                synapse,
                                name=self.name,
                                cell_type=target.cell_model.name,
                                cell_id=target.id,
                                synapse_type=synapse.synapse_name,
                            )


def _record_synaptic_current(result, synapse, **annotations):
    result.record(synapse._pp._ref_i, **annotations, units="nA")
