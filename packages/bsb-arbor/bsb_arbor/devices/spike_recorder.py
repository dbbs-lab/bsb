import collections

import neo
from bsb import config

from ..device import ArborDevice


@config.node
class SpikeRecorder(ArborDevice, classmap_entry="spike_recorder"):
    def boot(self):
        self._gids = set()

    def implement(self, adapter, simulation, simdata):
        super().implement(adapter, simulation, simdata)
        # Arbor distributes the cells itself and its Python API gathers the spikes,
        # so rank 0 holds the whole run's results and is by convention the rank
        # that writes them.
        if not adapter.comm.get_rank():

            def record_device_spikes(segment):
                times = collections.defaultdict(list)
                for (gid, index), time in simdata.arbor_sim.spikes():
                    if index == 0 and gid in self._gids:
                        times[gid].append(time)
                # One train per cell the device watched, empty ones included. Which
                # cells those were is then the set of recordings itself, so nothing
                # has to say it a second time, and a silent cell is told apart from
                # one that was never watched by reading the results alone.
                for gid in sorted(self._gids):
                    segment.spiketrains.append(
                        neo.SpikeTrain(
                            times[gid],
                            units="ms",
                            t_stop=self.simulation.duration,
                            name=self.name,
                            cell_id=gid,
                        )
                    )

            simdata.result.create_recorder(record_device_spikes, device=self)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []
