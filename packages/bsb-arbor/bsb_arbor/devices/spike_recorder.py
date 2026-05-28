from collections import defaultdict

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
                per_gid_times = defaultdict(list)
                for (gid, index), time in simdata.arbor_sim.spikes():
                    if index == 0 and gid in self._gids:
                        per_gid_times[int(gid)].append(time)

                for gid, times in per_gid_times.items():
                    cell_model = simdata.gid_manager.lookup_model(gid)
                    offset = simdata.gid_manager._gid_offsets[cell_model]
                    cell_id = gid - offset
                    ps_name = cell_model.cell_type.name
                    segment.spiketrains.append(
                        simdata.result.spike_train(
                            times=times,
                            ps_name=ps_name,
                            cell_id=cell_id,
                            cell_model=cell_model,
                            device=self,
                            t_stop=self.simulation.duration,
                        )
                    )

            simdata.result.create_recorder(record_device_spikes)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []
