from bsb import config

from ..device import ArborDevice


@config.node
class SpikeRecorder(ArborDevice, classmap_entry="spike_recorder"):
    def boot(self):
        self._gids = set()

    def implement(self, adapter, simulation, simdata):
        super().implement(adapter, simulation, simdata)
        if not adapter.comm.get_rank():
            targets = {}
            for gid in self._gids:
                model = simdata.gid_manager.lookup_model(gid)
                offset = simdata.gid_manager.lookup_offset(gid)
                targets.setdefault(model.cell_type.name, []).append(gid - offset)
            simdata.result.record_device_targets(self, targets)


            def record_device_spikes(segment):
                times = {}
                for (gid, index), time in simdata.arbor_sim.spikes():
                    if index == 0 and gid in self._gids:
                        times.setdefault(gid, []).append(time)
                # Driven by what spiked: a cell that stayed silent leaves no object,
                # and is recovered from the device's recorded target set.
                for gid, spikes in times.items():
                    model = simdata.gid_manager.lookup_model(gid)
                    offset = simdata.gid_manager.lookup_offset(gid)
                    segment.spiketrains.append(
                        simdata.result.spike_train(
                            times=spikes,
                            ps_name=model.cell_type.name,
                            cell_id=gid - offset,
                            cell_model=model,
                            device=self,
                            t_stop=self.simulation.duration,
                        )
                    )

            simdata.result.create_recorder(record_device_spikes, device=self)

    def implement_probes(self, simdata, gid):
        self._gids.add(gid)
        return []

    def implement_generators(self, simdata, gid):
        return []
