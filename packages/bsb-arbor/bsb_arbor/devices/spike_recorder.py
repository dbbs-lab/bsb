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
                # One train per cell that spiked. A cell that stayed silent writes
                # nothing: absence from the results is what silence looks like.
                #
                # A device none of whose cells spiked still writes one row of its
                # own, with no cell to name, or which cells it watched would be
                # lost with them and a silent population would be indexed from
                # nothing at all.
                for gid in sorted(times) or [None]:
                    segment.spiketrains.append(
                        neo.SpikeTrain(
                            times[gid] if gid is not None else [],
                            units="ms",
                            t_stop=self.simulation.duration,
                            name=self.name,
                            **({} if gid is None else {"cell_id": gid}),
                            # Which cells the device watched, so a silent cell is
                            # still answerable from the results alone.
                            gids=sorted(self._gids),
                            pop_size=len(self._gids),
                        )
                    )

            simdata.result.create_recorder(record_device_spikes, device=self)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []
