import neo
import numpy as np
from bsb import cell_annotations, config, multiplex_targets

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
                if not self._gids:
                    return
                # One roster entry per cell the device watches, silent ones included.
                # Which cells those were is then the roster itself, so nothing has to
                # say it a second time, and a silent cell is told apart from one that
                # was never watched by reading the results alone.
                sorted_gids = sorted(self._gids)
                index_of = {gid: index for index, gid in enumerate(sorted_gids)}
                targets = [
                    cell_annotations(*_cell_of_gid(simdata, gid), "record")
                    for gid in sorted_gids
                ]
                times = []
                target_index = []
                for (gid, probe_index), time in simdata.arbor_sim.spikes():
                    if probe_index == 0 and gid in index_of:
                        times.append(time)
                        target_index.append(index_of[gid])
                segment.spiketrains.append(
                    neo.SpikeTrain(
                        times,
                        units="ms",
                        t_stop=self.simulation.duration,
                        name="spikes",
                        array_annotations={
                            "bsb_target_index": np.array(target_index, dtype=int)
                        },
                        **multiplex_targets(targets),
                    )
                )

            simdata.result.create_recorder(record_device_spikes, device=self)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []


def _cell_of_gid(simdata, gid):
    """
    The cell model and cell id that an arbor gid simulates.

    Each model's gids start at its offset and follow its placement set row by row,
    so the cell id is the gid counted from there.
    """
    manager = simdata.gid_manager
    model = manager.lookup_model(gid)
    return model, gid - manager.lookup_offset(gid)
