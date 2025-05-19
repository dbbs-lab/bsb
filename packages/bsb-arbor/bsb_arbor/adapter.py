import itertools
import itertools as it
import time
import typing

import arbor
import numpy as np
from arbor import units as U
from bsb import (
    AdapterError,
    Chunk,
    SimulationData,
    SimulatorAdapter,
    UnknownGIDError,
    report,
    warn,
)

if typing.TYPE_CHECKING:
    from .simulation import ArborSimulation


class ArborSimulationData(SimulationData):
    """
    Container class for simulation data.
    """

    def __init__(self, simulation):
        """
        Container class for simulation data.
        """
        super().__init__(simulation)
        self.arbor_sim: arbor.simulation = None


class ReceiverCollection(list):
    """
    Receiver collections store the incoming connections and deduplicate them into multiple
    targets.
    """

    def __init__(self):
        super().__init__()
        self._endpoint_counters = {}

    def append(self, rcv):
        endpoint = str(rcv.loc_on)
        id = self._endpoint_counters.get(endpoint, 0)
        self._endpoint_counters[endpoint] = id + 1
        rcv.index = id
        super().append(rcv)


class SingleReceiverCollection(list):
    """
    The single receiver collection redirects all incoming connections to the same
    receiver.
    """

    def append(self, rcv):
        rcv.index = 0
        super().append(rcv)


class Population:
    def __init__(self, simdata, cell_model, offset):
        self._model = cell_model
        self._simdata = simdata
        ps = cell_model.get_placement_set(simdata.chunks)
        self._ranges = self._get_ranges(simdata.chunks, ps, offset)
        self._offset = offset

    @property
    def model(self):
        return self._model

    @property
    def offset(self):
        return self._offset

    def __len__(self):
        return sum(stop - start for start, stop in self._ranges)

    def __contains__(self, i):
        return any(start <= i < stop for start, stop in self._ranges)

    def copy(self):
        return Population(self._simdata, self._model, self._offset)

    def __getitem__(self, item):
        # Boolean masking, kind of
        if getattr(item, "dtype", None) == bool or _all_bools(item):  # noqa: E721
            if len(item) != len(self):
                raise ValueError(
                    f"Dimension mismatch between population ({len(self)}) "
                    f"and mask ({len(item)})"
                )
            return self._subpop_np(np.array(self)[item])
        elif getattr(item, "dtype", None) == int or _all_ints(item):  # noqa: E721
            if getattr(item, "ndim", None) == 0:
                return self._subpop_one(item)
            return self._subpop_np(np.array(self)[item])
        elif isinstance(item, slice):
            return self._subpop_np(np.array(self)[item])
        else:
            return self._subpop_one(item)

    def _get_ranges(self, chunks, ps, offset):
        stats = ps.get_chunk_stats()
        ranges = []
        for chunk, len_ in sorted(
            stats.items(), key=lambda k: Chunk.from_id(int(k[0]), None).id
        ):
            if chunk in chunks:
                ranges.append((offset, offset + len_))
            offset += len_
        return ranges

    def _subpop_np(self, arr):
        pop = self.copy()
        if not len(pop):
            return pop
        ranges = []
        prev = None
        start, stop = self._ranges[0]
        for i in arr:
            if prev is None:
                start += i
                stop = start + 1
            elif i == prev + 1:
                stop += 1
            else:
                ranges.append((start, stop))
                start = i
                stop = i + 1
            prev = i
        pop._ranges = ranges
        return pop

    def _subpop_one(self, item):
        if item >= len(self):
            raise IndexError(f"Index {item} out of bounds for size {len(self)}")
        pop = self.copy()
        ptr = 0
        for start, stop in self._ranges:
            if item < (ptr + stop - start):
                pop._ranges = [(start + ptr - item, start + ptr - item + 1)]
                return pop
            else:
                ptr += stop - start

    def __iter__(self):
        yield from itertools.chain.from_iterable(range(r[0], r[1]) for r in self._ranges)


class GIDManager:
    def __init__(self, simulation, simdata):
        self._gid_offsets = {}
        self._model_order = self.sort_models(simulation.cell_models.values())
        ctr = 0
        for model in self._model_order:
            self._gid_offsets[model] = ctr
            ctr += len(model.get_placement_set())
        self._populations = [
            Population(simdata, model, offset)
            for model, offset in self._gid_offsets.items()
        ]

    def sort_models(self, models):
        return sorted(
            models,
            key=lambda model: len(model.get_placement_set()),
        )

    def lookup_offset(self, gid):
        model = self.lookup_model(gid)
        return self._gid_offsets[model]

    def lookup_kind(self, gid):
        return self._lookup(gid).model.get_cell_kind(gid)

    def lookup_model(self, gid):
        return self._lookup(gid).model

    def _lookup(self, gid):
        try:
            return next(c for c in self._populations if gid in c)
        except StopIteration:
            raise UnknownGIDError(f"Can't find gid {gid}.") from None

    def all(self):
        yield from itertools.chain.from_iterable(self._populations)

    def get_populations(self):
        return {pop.model: pop for pop in self._populations}


class ArborRecipe(arbor.recipe):
    def __init__(self, simulation, simdata):
        super().__init__()
        self._simulation = simulation
        self._simdata = simdata
        self._global_properties = arbor.neuron_cable_properties()
        self._global_properties.set_property(
            Vm=-65 * U.mV,
            tempK=300 * U.Kelvin,
            rL=35.4 * U.Ohm * U.cm,
            cm=0.01 * U.F / U.m2,
        )
        self._global_properties.set_ion(
            ion="na", int_con=10 * U.mM, ext_con=140 * U.mM, rev_pot=50 * U.mM
        )
        self._global_properties.set_ion(
            ion="k", int_con=54.4 * U.mM, ext_con=2.5 * U.mM, rev_pot=-77 * U.mM
        )
        self._global_properties.set_ion(
            ion="ca", int_con=0.0001 * U.mM, ext_con=2 * U.mM, rev_pot=132.5 * U.mM
        )
        self._global_properties.set_ion(
            ion="h",
            valence=1,
            int_con=1.0 * U.mM,
            ext_con=1.0 * U.mM,
            rev_pot=-34 * U.mM,
        )
        self._global_properties.catalogue = self._get_catalogue()

    def _get_catalogue(self):
        catalogue = arbor.default_catalogue()
        prefixes = set()
        for model in self._simulation.cell_models.values():
            prefix, model_catalogue = model.get_prefixed_catalogue()
            if model_catalogue is not None and prefix not in prefixes:
                prefixes.add(prefix)
                catalogue.extend(model_catalogue, "")

        return catalogue

    def global_properties(self, kind):
        return self._global_properties

    def num_cells(self):
        return sum(
            len(model.get_placement_set())
            for model in self._simulation.cell_models.values()
        )

    def cell_kind(self, gid):
        return self._simdata.gid_manager.lookup_kind(gid)

    def cell_description(self, gid):
        model = self._simdata.gid_manager.lookup_model(gid)
        return model.get_description(gid)

    def connections_on(self, gid):
        return [
            arbor.connection(rcv.from_(), rcv.on(), rcv.weight, rcv.delay * U.ms)
            for rcv in self._simdata.connections_on[gid]
        ]

    def gap_junctions_on(self, gid):
        return [
            c.model.gap_junction(c) for c in self._simdata.gap_junctions_on.get(gid, [])
        ]

    def probes(self, gid):
        devices = self._simdata.devices_on[gid]
        _ntag = 0
        probes = []
        for device in devices:
            device_probes = device.implement_probes(self._simdata, gid)
            for tag in range(_ntag, _ntag + len(device_probes)):
                device.register_probe_id(gid, tag)
            probes.extend(device_probes)
        return probes

    def event_generators(self, gid):
        devices = self._simdata.devices_on[gid]
        generators = []
        for device in devices:
            device_generators = device.implement_generators(self._simdata, gid)
            generators.extend(device_generators)
        return generators

    def _name_of(self, gid):
        return self._simdata.gid_manager.lookup_model(gid).cell_type.name


class ArborAdapter(SimulatorAdapter):
    def __init__(self, comm=None):
        super().__init__(comm)
        self.simdata: dict[ArborSimulation, ArborSimulationData] = {}

    def prepare(self, simulation: "ArborSimulation") -> ArborSimulationData:
        """
        Prepares the arbor simulation engine with the given simulation.
        """
        simdata = self._create_simdata(simulation)
        try:
            context = arbor.context(arbor.proc_allocation(threads=simulation.threads))
            if self.comm.get_size() > 1:
                if not arbor.config()["mpi4py"]:
                    warn(
                        f"Arbor does not seem to be built with MPI support, running"
                        f"duplicate simulations on {self.comm.get_size()} nodes."
                    )
                else:
                    context = arbor.context(
                        arbor.proc_allocation(threads=simulation.threads),
                        mpi=self.comm.get_communicator(),
                    )
            if simulation.profiling:
                if arbor.config()["profiling"]:
                    report("enabling profiler", level=2)
                    arbor.profiler_initialize(context)
                else:
                    raise RuntimeError(
                        "Arbor must be built with profiling support to use the "
                        "`profiling` flag."
                    )
            simdata.gid_manager = self.get_gid_manager(simulation, simdata)
            simdata.populations = simdata.gid_manager.get_populations()
            report("preparing simulation", level=1)
            report("MPI processes:", context.ranks, level=2)
            report("Threads per process:", context.threads, level=2)
            recipe = self.get_recipe(simulation, simdata)
            # Gap junctions are required for domain decomposition
            self.domain = arbor.partition_load_balance(recipe, context)
            self.gids = set(it.chain.from_iterable(g.gids for g in self.domain.groups))
            simdata.arbor_sim = arbor.simulation(recipe, context, self.domain)
            self.prepare_samples(simulation, simdata)
            report("prepared simulation", level=1)
            return simdata
        except Exception:
            del self.simdata[simulation]
            raise

    def get_gid_manager(self, simulation, simdata):
        return GIDManager(simulation, simdata)

    def prepare_samples(self, simulation, simdata):
        for device in simulation.devices.values():
            device.prepare_samples(simdata, comm=self.comm)

    def run(self, *simulations):
        if len(simulations) != 1:
            raise RuntimeError(
                "Can not run multiple simultaneous simulations. Composition not "
                "implemented."
            )
        simulation = simulations[0]
        try:
            simdata = self.simdata[simulation]
            arbor_sim = simdata.arbor_sim
        except KeyError:
            raise AdapterError(
                f"Can't run unprepared simulation '{simulation.name}'"
            ) from None
        try:
            if not self.comm.get_rank():
                arbor_sim.record(arbor.spike_recording.all)

            start = time.time()
            report("running simulation", level=1)
            arbor_sim.run(simulation.duration * U.ms, dt=simulation.resolution * U.ms)
            report(f"completed simulation. {time.time() - start:.2f}s", level=1)
            if simulation.profiling and arbor.config()["profiling"]:
                report("printing profiler summary", level=2)
                report(arbor.profiler_summary(), level=1)
            return [simdata.result]
        finally:
            del self.simdata[simulation]

    def get_recipe(self, simulation, simdata=None):
        if simdata is None:
            simdata = self._create_simdata(simulation)
        self._cache_gap_junctions(simulation, simdata)
        self._cache_connections(simulation, simdata)
        self._cache_devices(simulation, simdata)
        return ArborRecipe(simulation, simdata)

    def _create_simdata(self, simulation):
        self.simdata[simulation] = simdata = ArborSimulationData(simulation)
        self._assign_chunks(simulation, simdata)
        return simdata

    def _cache_gap_junctions(self, simulation, simdata):
        simdata.gap_junctions_on = {}
        for conn_model in simulation.connection_models.values():
            if conn_model.gap:
                conn_set = conn_model.get_connectivity_set()
                conns = conn_set.load_connections().to(simdata.chunks).as_globals()
                conn_model.create_gap_junctions_on(simdata.gap_junctions_on, conns)

    def _cache_connections(self, simulation, simdata):
        simdata.connections_on = {
            gid: simdata.gid_manager.lookup_model(gid).make_receiver_collection()
            for gid in simdata.gid_manager.all()
        }
        simdata.connections_from = {gid: [] for gid in simdata.gid_manager.all()}
        for conn_model in simulation.connection_models.values():
            if conn_model.gap:
                continue
            conn_set = conn_model.get_connectivity_set()
            pop_pre, pop_post = None, None
            for model in simulation.cell_models.values():
                if model.cell_type is conn_set.pre_type:
                    pop_pre = simdata.populations[model]
                if model.cell_type is conn_set.post_type:
                    pop_post = simdata.populations[model]
            # Get the arriving connection iterator
            conns_on = conn_set.load_connections().to(simdata.chunks).as_globals()
            # Create the arriving connections
            conn_model.create_connections_on(
                simdata.connections_on, conns_on, pop_pre, pop_post
            )
            # Get the outgoing connection iterator
            conns_from = conn_set.load_connections().from_(simdata.chunks).as_globals()
            # Create the outgoing connections
            conn_model.create_connections_from(
                simdata.connections_from, conns_from, pop_pre, pop_post
            )

    def _cache_devices(self, simulation, simdata):
        simdata.devices_on = {gid: [] for gid in simdata.gid_manager.all()}
        for device in simulation.devices.values():
            targets = device.targetting.get_targets(self, simulation, simdata)
            for target in itertools.chain.from_iterable(targets.values()):
                simdata.devices_on[target].append(device)

    def _assign_chunks(self, simulation, simdata):
        chunk_stats = simulation.scaffold.storage.get_chunk_stats()
        size = self.comm.get_size()
        all_chunks = [Chunk.from_id(int(chunk), None) for chunk in chunk_stats]
        simdata.node_chunk_alloc = [all_chunks[rank::size] for rank in range(0, size)]
        simdata.chunk_node_map = {}
        for node, chunks in enumerate(simdata.node_chunk_alloc):
            for chunk in chunks:
                simdata.chunk_node_map[chunk] = node
        simdata.chunks = simdata.node_chunk_alloc[self.comm.get_rank()]


def _all_bools(arr):
    try:
        return all(isinstance(b, bool) for b in arr)
    except TypeError:
        # Not iterable
        return False


def _all_ints(arr):
    try:
        return all(isinstance(b, int) for b in arr)
    except TypeError:
        # Not iterable
        return False
