from bsb import LocationTargetting, config, types

from ..device import NeuronDevice


@config.node
class SpikeGenerator(NeuronDevice, classmap_entry="spike_generator"):
    locations = config.attr(type=LocationTargetting, default={"strategy": "soma"})
    synapses = config.list()
    parameters = config.catch_all(type=types.any_())

    def implement(self, adapter, simulation, simdata):
        for _model, pop in self.targetting.get_targets(
            adapter, simulation, simdata
        ).items():
            for target in pop:
                for location in self.locations.get_locations(target):
                    for synapse in location.section.synapses:
                        if not self.synapses or synapse.synapse_name in self.synapses:
                            synapse.stimulate(**self.parameters)
