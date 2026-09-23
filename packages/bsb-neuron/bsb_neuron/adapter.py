import itertools

import numpy as np
from bsb import (
    AdapterError,
    Chunk,
    DatasetNotFoundError,
    ResultsError,
    SimulationData,
    SimulationError,
    SimulationResult,
    SimulatorAdapter,
    multiplex_channels,
    report,
)
from neo import AnalogSignal


class NeuronSimulationData(SimulationData):
    def __init__(self, simulation, result=None):
        """
        type simulation: bsb.simulation.simulation.Simulation
        """
        super().__init__(simulation, result=result)
        self.cid_offsets = dict()
        self.connections = dict()


class NeuronResult(SimulationResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # A device's channels, recorded across however many calls to `record` it
        # makes, one flush of one multiplexed signal apiece: keyed on the device, not
        # drawn per call, so every point/synapse of a device lands in the one signal.
        self._channels = {}

    def record(self, obj, *, device, target: dict, name: str, units: str):
        """
        Record a NEURON variable every time step, as a recording of a device.

        Every call for the same device joins one multiplexed signal, flushed as a
        single ``AnalogSignal`` with one channel per call, rather than one signal per
        call: cheap to write and to merge across ranks, at the scale of a device
        rather than the scale of a cell.

        :param obj: Reference to the NEURON variable to record, such as ``seg._ref_v``.
        :param device: The device the recording belongs to.
        :type device: bsb_neuron.device.NeuronDevice
        :param target: What is recorded, as the annotations of
          :func:`~bsb.simulation.results.cell_annotations`,
          :func:`~bsb.simulation.results.point_annotations` or
          :func:`~bsb.simulation.results.synapse_annotations` give them.
        :param name: What the recorded variable measures, such as ``v`` or ``i``. Has
          to agree with every other call for the same device.
        :param units: Units of the recorded variable. Has to agree with every other
          call for the same device.
        """
        from patch import p

        if "bsb_recording_kind" not in target or "bsb_direction" not in target:
            raise AdapterError(
                f"Device '{device.name}' has to say what it records: pass the "
                "annotations of `cell_annotations`, `point_annotations` or "
                "`synapse_annotations` as `target`."
            )
        entry = self._channels.get(device)
        if entry is None:
            entry = self._channels[device] = {
                "name": name,
                "units": units,
                "channels": [],
            }
            self.create_recorder(
                lambda segment: self._flush_device(segment, device), device=device
            )
        elif entry["name"] != name or entry["units"] != units:
            raise AdapterError(
                f"Device '{device.name}' recorded '{entry['name']}' in "
                f"'{entry['units']}' before, and now '{name}' in '{units}': every "
                "channel of a device has to measure the same thing, in the same units."
            )
        entry["channels"].append((p.record(obj), target))

    def _flush_device(self, segment, device):
        """Combine every channel a device recorded since the last flush into one
        multiplexed ``AnalogSignal``, and free the NEURON vectors that held them."""
        from patch import p
        from quantities import ms

        entry = self._channels[device]
        channels = entry["channels"]
        lengths = {v.size() for v, _ in channels}
        if len(lengths) > 1:
            raise ResultsError(
                f"Device '{device.name}' recorded channels of different lengths "
                f"{sorted(lengths)} this checkpoint; they cannot be combined into one "
                "signal."
            )
        data = np.array([list(v) for v, _ in channels]).T
        baseline, array_annotations = multiplex_channels(
            [target for _, target in channels]
        )
        segment.analogsignals.append(
            AnalogSignal(
                data,
                sampling_period=p.dt * ms,
                name=entry["name"],
                units=entry["units"],
                array_annotations=array_annotations,
                **baseline,
            )
        )
        # Free the memory
        for v, _ in channels:
            if v.size():
                v.remove(0, v.size() - 1)


class NeuronAdapter(SimulatorAdapter):
    initial = -65

    def __init__(self, comm=None):
        super().__init__(comm=comm)
        self.network = None
        self.next_gid = 0

    @property
    def engine(self):
        from patch import p as engine

        return engine

    def prepare(self, simulation, filename=None):
        """
        Prepare the simulation environment and data structures for running a NEURON
        simulation.

        This method initializes simulation-specific data, sets simulation parameters
        such as time resolution, temperature, and duration in the NEURON engine,
        performs load balancing across compute nodes, and creates neurons, connections,
        and devices according to the simulation configuration.

        :param simulation: The simulation instance to prepare.
        :type simulation: bsb.simulation.simulation.Simulation
        :return: The prepared simulation data container.
        :rtype: NeuronSimulationData

        :raises: Propagates any exceptions raised during preparation, and cleans up
            partial data on failure.
        """

        self.simdata[simulation] = NeuronSimulationData(
            simulation,
            result=NeuronResult(
                simulation,
                filename=filename,
                comm=self.comm,
                simulation_id=self.new_run_id(),
            ),
        )
        try:
            report("Preparing simulation", level=2)
            self.engine.dt = simulation.resolution
            self.engine.celsius = simulation.temperature
            self.engine.tstop = simulation.duration
            report("Load balancing", level=2)
            self.load_balance(simulation)
            report("Creating neurons", level=2)
            self.create_neurons(simulation)
            report("Creating transmitters", level=2)
            self.create_connections(simulation)
            report("Creating devices", level=2)
            self.implement_components(simulation)
            self.load_controllers(simulation)
            return self.simdata[simulation]
        except:
            del self.simdata[simulation]
            raise

    def load_balance(self, simulation):
        simdata = self.simdata[simulation]
        chunk_stats = simulation.scaffold.storage.get_chunk_stats()
        size = self.comm.get_size()
        all_chunks = [Chunk.from_id(int(chunk), None) for chunk in chunk_stats]
        simdata.node_chunk_alloc = [all_chunks[rank::size] for rank in range(0, size)]
        simdata.chunk_node_map = {}
        for node, chunks in enumerate(simdata.node_chunk_alloc):
            for chunk in chunks:
                simdata.chunk_node_map[chunk] = node
        simdata.chunks = simdata.node_chunk_alloc[self.comm.get_rank()]
        simdata.placement = {
            model: model.get_placement_set(chunks=simdata.chunks)
            for model in simulation.cell_models.values()
        }

    def run(self, *simulations):
        """
        :type simulations: list[bsb.simulation.simulation.Simulation]
        """
        unprepared = [sim for sim in simulations if sim not in self.simdata]
        if unprepared:
            raise AdapterError(f"Unprepared for simulations: {', '.join(unprepared)}")
        try:
            report("Simulating...", level=2)
            pc = self.engine.ParallelContext()
            pc.set_maxstep(10)
            self.engine.finitialize(self.initial)
            self._duration = max(sim.duration for sim in simulations)

            for t, checkpoint_controllers in self.get_next_checkpoint():
                pc.psolve(t)
                self.execute_checkpoints(checkpoint_controllers)

            report("Finished simulation.", level=2)
        finally:
            results = [self.simdata[sim].result for sim in simulations]
            for sim in simulations:
                del self.simdata[sim]
        return results

    def create_neurons(self, simulation):
        simdata = self.simdata[simulation]
        offset = 0
        for cell_model in sorted(simulation.cell_models.values()):
            ps = cell_model.get_placement_set()
            simdata.cid_offsets[cell_model.cell_type] = offset
            with ps.chunk_context(simdata.chunks):
                if (len(ps)) != 0:
                    self._create_population(simdata, cell_model, ps, offset)
                    offset += len(ps)
                else:
                    simdata.populations[cell_model] = NeuronPopulation(cell_model, [])

    def create_connections(self, simulation):
        simdata = self.simdata[simulation]
        self._allocate_transmitters(simulation)
        for conn_model in simulation.connection_models.values():
            cs = simulation.scaffold.get_connectivity_set(conn_model.name)
            simdata.connections[conn_model] = conn_model.create_connections(
                simulation, simdata, cs
            )

    def _allocate_transmitters(self, simulation):
        simdata = self.simdata[simulation]
        first = self.next_gid
        chunk_stats = simulation.scaffold.storage.get_chunk_stats()
        max_trans = sum(stats["connections"]["out"] for stats in chunk_stats.values())
        report(
            f"Allocated GIDs {first} to {first + max_trans}",
            level=3,
        )
        self.next_gid += max_trans
        simdata.alloc = (first, self.next_gid)
        simdata.transmap = self._map_transceivers(simulation, simdata)

    def _map_transceivers(self, simulation, simdata):
        offset = 0
        transmap = {}

        pre_types = set(cs.pre_type for cs in simulation.get_connectivity_sets().values())
        for pre_type in sorted(pre_types, key=lambda pre_type: pre_type.name):
            data = []
            for _cm, cs in simulation.get_connectivity_sets().items():
                if cs.pre_type != pre_type:
                    continue
                pre, _ = cs.load_connections().as_globals().all()
                data.append(pre[:, :2])

            data = self.better_concat(data)
            # Save all transmitters of the same pre_type across connectivity sets
            all_cm_transmitters = np.unique(data, axis=0)
            for cm, cs in simulation.get_connectivity_sets().items():
                if cs.pre_type != pre_type:
                    continue

                # Now look up which transmitters are on our chunks
                pre_t, _ = cs.load_connections().from_(simdata.chunks).as_globals().all()
                our_cm_transmitters = np.unique(pre_t[:, :2], axis=0)
                # Look up the local ids of those transmitters
                pre_lc, _ = cs.load_connections().from_(simdata.chunks).all()
                local_cm_transmitters = np.unique(pre_lc[:, :2], axis=0)

                # Find the common indexes between all the transmitters, and the
                # transmitters on our chunk.
                dtype = ", ".join([str(all_cm_transmitters.dtype)] * 2)
                _, _, idx_tm = np.intersect1d(
                    our_cm_transmitters.view(dtype),
                    all_cm_transmitters.view(dtype),
                    assume_unique=True,
                    return_indices=True,
                )

                # Look up which transmitters have receivers on our chunks
                pre_gc, _ = cs.load_connections().incoming().to(simdata.chunks).all()
                local_cm_receivers = np.unique(pre_gc[:, :2], axis=0)
                _, _, idx_rcv = np.intersect1d(
                    local_cm_receivers.view(dtype),
                    all_cm_transmitters.view(dtype),
                    assume_unique=True,
                    return_indices=True,
                )

                # Store a map of the local chunk transmitters to their GIDs
                transmap[cm] = {
                    "transmitters": dict(
                        zip(
                            map(tuple, local_cm_transmitters),
                            map(int, idx_tm + offset),
                            strict=False,
                        )
                    ),
                    "receivers": dict(
                        zip(
                            map(tuple, local_cm_receivers),
                            map(int, idx_rcv + offset),
                            strict=False,
                        )
                    ),
                }

            # Offset by the total amount of transmitter GIDs used by this ConnSet.
            offset += len(all_cm_transmitters)
        return transmap

    def better_concat(self, items):
        if not items:
            raise RuntimeError("Can not concat 0 items")
        l_ = sum(len(x) for x in items)
        r = np.empty((l_, items[0].shape[1]), dtype=items[0].dtype)
        ptr = 0
        for x in items:
            r[ptr : ptr + len(x)] = x
            ptr += len(x)
        return r

    def _create_population(self, simdata, cell_model, ps, offset):
        data = []
        for var in (
            "ids",
            "positions",
            "morphologies",
            "rotations",
            "additional",
        ):
            try:
                data.append(getattr(ps, f"load_{var}")())
            except DatasetNotFoundError:
                data.append(itertools.repeat(None))

        instances = cell_model.create_instances(len(ps), *data)
        simdata.populations[cell_model] = NeuronPopulation(cell_model, instances)


class NeuronPopulation(list):
    def __init__(self, model, instances: list):
        """
        :type model: bsb_neuron.cell.NeuronCell
        """
        self._model = model
        super().__init__(instances)
        for instance in instances:
            instance.cell_model = model

    def __getitem__(self, item):
        # Boolean masking, kind of
        if getattr(item, "dtype", None) is bool or _all_bools(item):
            if len(self) == len(item):
                return NeuronPopulation(
                    self._model, [p for p, b in zip(self, item, strict=False) if b]
                )
            else:
                raise SimulationError
        elif getattr(item, "dtype", None) is int or _all_ints(item):
            if getattr(item, "ndim", None) == 0:
                return super().__getitem__(item)
            return NeuronPopulation(self._model, [self[i] for i in item])
        else:
            return super().__getitem__(item)


def _all_bools(arr):
    try:
        return all(np.issubdtype(type(b), np.bool_) for b in arr)
    except TypeError:
        # Not iterable
        return False


def _all_ints(arr):
    try:
        return all(np.issubdtype(type(b), np.integer) for b in arr)
    except TypeError:
        # Not iterable
        return False
