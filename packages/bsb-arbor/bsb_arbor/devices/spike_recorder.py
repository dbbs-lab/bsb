import neo
from bsb import config

from ..device import ArborDevice


@config.node
class SpikeRecorder(ArborDevice, classmap_entry="spike_recorder"):
    def boot(self):
        self._gids = set()

    def implement(self, adapter, simulation, simdata):
        super().implement(adapter, simulation, simdata)
        if not adapter.comm.get_rank():

            def record_device_spikes(segment):
                spiketrain = list()
                senders = list()
                for (gid, index), time in simdata.arbor_sim.spikes():
                    if index == 0 and gid in self._gids:
                        spiketrain.append(time)
                        senders.append(gid)
                segment.spiketrains.append(
                    neo.SpikeTrain(
                        spiketrain,
                        units="ms",
                        array_annotations={"senders": senders},
                        t_stop=self.simulation.duration,
                        device=self.name,
                        gids=list(self._gids),
                        pop_size=len(self._gids),
                    )
                )

            simdata.result.create_recorder(record_device_spikes)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []
