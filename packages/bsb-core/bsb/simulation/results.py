import dataclasses
import pathlib
import shutil
import traceback
import typing
import uuid
import warnings
from datetime import datetime

from ..exceptions import (
    DatasetNotFoundError,
    ResultsError,
    ResultsMismatchError,
    ResultsWarning,
)
from ..reporting import warn
from ..services import MPI
from ..storage.provenance import (
    collect_host_info,
    collect_plugin_manifest,
    decode_annotation,
    encode_annotation,
    get_provenance_version,
    iso_now,
)

if typing.TYPE_CHECKING:  # pragma: nocover
    import os

    import neo
    import numpy

    from ..cell_types import CellType
    from ..core import Scaffold
    from ..storage.interfaces import PlacementSet
    from .simulation import Simulation


def read_simulation_config(block: "neo.core.Block") -> dict | None:
    """
    Read the configuration of the simulation that produced a block of results.

    :param block: Block of results, either taken from a
        :class:`~bsb.simulation.results.SimulationResult` or read back out of a
        results file.
    :type block: neo.core.Block
    :returns: The configuration tree of the simulation, or ``None`` if the block
        carries none. A file written before the configuration was encoded carries
        only the tree's top-level keys, which are returned as they were found,
        after a warning: the values were never written and cannot be recovered.
    :rtype: dict | None
    """
    stored = block.annotations.get("config")
    decoded = decode_annotation(stored)
    if decoded is not None and not isinstance(decoded, dict):
        warn(
            f"Block '{block.name}' carries a simulation configuration written before "
            "it was stored intact; only its top-level keys were ever written to file."
        )
    return decoded


def read_provenance(block: "neo.core.Block") -> dict | None:
    """
    Read the provenance of the run that produced a block of results.

    An unrecognised schema version warns and returns what is there rather than
    refusing: the recordings themselves are plain neo and readable regardless, and
    refusing a file over metadata written by a newer BSB would keep someone from
    results that are perfectly intact.

    :param block: Block of results.
    :type block: neo.core.Block
    :returns: The provenance bundle, or ``None`` if the block carries none.
    :rtype: dict | None
    """
    bundle = decode_annotation(block.annotations.get("bsb_provenance"))
    if not isinstance(bundle, dict):
        return None
    version = bundle.get("schema_version")
    ours = get_provenance_version()
    if version is not None and version > ours:
        warn(
            f"Results of '{block.name}' were written with provenance schema "
            f"{version}, newer than this BSB's {ours}. Reading what is "
            "recognised; some metadata may be missing."
        )
    return bundle


def rank_part_path(filename, rank: int) -> pathlib.Path:
    """
    Where one rank writes its share of a run's results.

    Parts live in a sibling directory of the file they will become, so the finished
    result keeps the path it was asked for.

    :param filename: The final results file.
    :param rank: The rank writing this part.
    :returns: Path of that rank's part.
    """
    final = pathlib.Path(filename)
    return final.with_suffix(final.suffix + ".ranks") / f"rank{rank}.nio"


def merge_rank_results(parts, filename) -> None:
    """
    Concatenate per-rank results into one file.

    Ranks record disjoint cells, so a merge is a concatenation and never has to
    reconcile two accounts of the same recording. Segments are matched on their
    ``checkpoint_index``, which is what makes them line up across parts: a
    checkpoint is one segment holding every rank's share of it.

    That matching is why this holds a simulation's merged recordings in memory
    before writing them: a segment cannot be written until every part that has a
    share of it has been read. Peak memory is therefore one simulation's results,
    not the whole file, and each part is closed as soon as it has been merged.

    :param parts: The per-rank files, in rank order.
    :param filename: The file to write.
    """
    from neo import io

    merged = {}
    order = []
    for part in parts:
        with io.NixIO(str(part), "ro") as reader:
            blocks = reader.read_all_blocks()
        for block in blocks:
            key = block.annotations.get("bsb_simulation_id") or block.name
            if key not in merged:
                merged[key] = block
                order.append(key)
                continue
            into = merged[key]
            by_checkpoint = {
                segment.annotations.get("checkpoint_index", index): segment
                for index, segment in enumerate(into.segments)
            }
            for index, segment in enumerate(block.segments):
                checkpoint = segment.annotations.get("checkpoint_index", index)
                target = by_checkpoint.get(checkpoint)
                if target is None:
                    into.segments.append(segment)
                    by_checkpoint[checkpoint] = segment
                    continue
                target.spiketrains.extend(segment.spiketrains)
                target.analogsignals.extend(segment.analogsignals)
                target.events.extend(segment.events)

    with io.NixIO(str(filename), mode="ow") as out:
        for key in order:
            # Dropped as it is written, so a file of several simulations never has
            # more than the one being written on top of the ones already out.
            out.write_block(merged.pop(key))


#: The Neo containers a recording can land in, in the order a reader sees them.
_RECORDING_LISTS = ("spiketrains", "analogsignals")


def _recording_counts(segment) -> dict:
    """How many recordings the segment holds per container, to spot new ones."""
    return {name: len(getattr(segment, name)) for name in _RECORDING_LISTS}


def _stamp_device(segment, before: dict, device_name) -> None:
    """
    Annotate what a recorder just appended with the device it came from.

    The device is stamped here rather than by each recorder so that every backend
    answers "which device produced this?" the same way, without every device
    author having to remember to say so. A recorder that already named a device
    keeps its own answer.
    """
    if device_name is None:
        return
    for name in _RECORDING_LISTS:
        recordings = getattr(segment, name)
        for recording in recordings[before[name] :]:
            recording.annotations.setdefault("device", device_name)


@dataclasses.dataclass(frozen=True)
class Recording:
    """
    One recording and the cell it came from.

    Recordings are written one per cell, so this is the unit a reader iterates:
    it says which device produced the signal and which cell it belongs to,
    whatever backend ran the simulation and whichever Neo container it landed in.

    A cell is named by its cell model and its id in that model's placement set, never
    by a simulator's own id, so the pair addresses one row of the network:
    ``simulation.cell_models[cell_model].cell_type.get_placement_set()``, row
    ``cell_id``.
    """

    #: Name of the device that produced the recording.
    device: str | None
    #: Id of the cell in the placement set of its cell model, or ``None`` for a
    #: device level record such as a generator's own spikes. Only unique within
    #: :attr:`cell_model`.
    cell_id: int | None
    #: Name of the simulation's cell model the cell belongs to, or ``None`` for a
    #: device level record.
    cell_model: str | None
    #: The Neo object itself, a ``SpikeTrain`` or an ``AnalogSignal``.
    signal: typing.Any

    @property
    def is_spike_train(self) -> bool:
        return type(self.signal).__name__ == "SpikeTrain"


def iter_recordings(
    source,
    device: str | None = None,
    cell_id: int | None = None,
    cell_model: str | None = None,
) -> "typing.Iterator[Recording]":
    """
    Iterate the recordings of a block, a segment, or a list of either.

    :param source: What to read: a :class:`neo.core.Block`, a
        :class:`neo.core.Segment`, or an iterable of either.
    :param device: Only yield recordings made by this device.
    :param cell_id: Only yield recordings of cells with this id. A cell id is only
        unique within its cell model, so pass ``cell_model`` along to single out one
        cell.
    :param cell_model: Only yield recordings of cells of this cell model.
    :returns: The recordings, in the order they were written.
    :rtype: typing.Iterator[Recording]
    """
    for segment in _iter_segments(source):
        for name in _RECORDING_LISTS:
            for signal in getattr(segment, name, ()):
                annotations = signal.annotations
                recording = Recording(
                    device=annotations.get("device"),
                    cell_id=annotations.get("cell_id"),
                    cell_model=annotations.get("cell_model"),
                    signal=signal,
                )
                if device is not None and recording.device != device:
                    continue
                if cell_model is not None and recording.cell_model != cell_model:
                    continue
                if cell_id is not None and recording.cell_id != cell_id:
                    continue
                yield recording


def _iter_segments(source):
    """Take a block, a segment, or any nesting of them, and yield the segments."""
    if hasattr(source, "segments"):
        yield from source.segments
    elif hasattr(source, "spiketrains"):
        yield source
    else:
        for item in source:
            yield from _iter_segments(item)


class SimulationResult:
    """
    The results of one simulation, and the provenance of the run that made them.

    Under MPI each rank writes its own part and rank 0 merges them into the file
    that was asked for, because neither ``nixio`` nor an HDF5 attribute supports
    concurrent writers. The parts are an implementation detail: a run ends with one
    file, and ``finalize`` is what makes that true.
    """

    def __init__(self, simulation, filename=None, comm=None, simulation_id=None):
        """
        :param comm: The communicator whose ranks share this run, which is the
          adapter's. It decides who takes part in ``finalize`` and which parts it
          expects to find, so an adapter given a sub-communicator has to hand it on
          rather than let this fall back to the world.
        :param simulation_id: The identity of the run, which every rank writing a part
          of it has to agree on, or the parts cannot be recognised as belonging
          together. An adapter agrees one with :meth:`SimulatorAdapter.new_run_id
          <bsb.simulation.adapter.SimulatorAdapter.new_run_id>` and passes it here.
          Constructing this without one is for a result that stands alone: a fresh
          identity is made up locally, since there is nobody to agree with.
        """
        from neo import Block

        self.comm = comm or MPI
        self.simulation = simulation
        self.recorders = []
        self.checkpoint_index = 0
        self._t_cursor = 0.0

        self.simulation_id = simulation_id or str(uuid.uuid4())

        # Kept as the caller gave it; paths are derived where they are needed, so a
        # caller that passed a string still reads one back.
        self.filename = filename
        self.part_filename = (
            rank_part_path(filename, self.comm.get_rank())
            if filename is not None and self.comm.get_size() > 1
            else filename
        )

        tree = simulation.__tree__()
        block = Block(
            name=simulation.name,
            config=encode_annotation(tree, "simulation configuration with the results"),
        )
        block.annotate(
            bsb_simulation_id=self.simulation_id,
            bsb_provenance=encode_annotation(
                self._build_provenance(simulation), "simulation provenance"
            ),
        )
        block.rec_datetime = datetime.now()

        if self.part_filename is not None:
            from neo import io

            pathlib.Path(self.part_filename).parent.mkdir(parents=True, exist_ok=True)
            self._block = None
            with io.NixIO(str(self.part_filename), mode="rw") as out:
                run_index = sum(
                    1
                    for nb in out.nix_file.blocks
                    if nb.metadata
                    and "neo_name" in nb.metadata
                    and nb.metadata["neo_name"] == simulation.name
                )
                block.annotate(sim_name=simulation.name, run_index=run_index)
                out.write_block(block)
                self.block_key = block.annotations["nix_name"]
        else:
            self._block = block

    def _build_provenance(self, simulation) -> dict:
        scaffold = getattr(simulation, "scaffold", None)
        return {
            "schema_version": get_provenance_version(),
            "simulation_id": self.simulation_id,
            "simulation_name": simulation.name,
            "started_at": iso_now(),
            "duration_ms": getattr(simulation, "duration", None),
            "resolution_ms": getattr(simulation, "resolution", None),
            "seed": self._seed_of(scaffold),
            "scaffold": {
                "storage_id": getattr(scaffold, "storage_id", None),
                "state_id": getattr(scaffold, "state_id", None),
            },
            "plugins": collect_plugin_manifest(),
            # `host` differs per rank on a cluster and `mpi_rank` is gone from the
            # file once the parts are merged, so the diagnostics are per rank.
            "ranks": [
                {
                    "mpi_rank": self.comm.get_rank(),
                    "host": collect_host_info(),
                }
            ],
            "mpi_size": self.comm.get_size(),
        }

    @staticmethod
    def _seed_of(scaffold):
        try:
            return scaffold.configuration.rng.seed
        except AttributeError:
            return None

    @property
    def block(self):
        if self._block is None:
            raise RuntimeError(
                f"Results were streamed to '{self.part_filename}'; read them back "
                "from the file, not from the result object."
            )
        return self._block

    def add(self, recorder):
        self.recorders.append(recorder)

    def create_recorder(
        self, flush: typing.Callable[["neo.core.Segment"], None], device=None
    ):
        recorder = SimulationRecorder(device=device)
        recorder.flush = flush
        self.add(recorder)
        return recorder

    def flush(self):
        from neo import Segment

        segment = Segment()
        t_stop = float(getattr(self.simulation, "duration", 0.0) or 0.0)
        segment.annotate(
            # Segments of one run are matched across rank files by this, so it is
            # derived rather than drawn: a per-rank id would never line up.
            segment_id=f"{self.simulation_id}:{self.checkpoint_index}",
            checkpoint_index=self.checkpoint_index,
            t_start_ms=self._t_cursor,
            t_stop_ms=t_stop,
            mpi_rank=self.comm.get_rank(),
        )
        for recorder in self.recorders:
            before = _recording_counts(segment)
            try:
                recorder.flush(segment)
            except Exception:
                traceback.print_exc()
                warn("Recorder errored out!")
            finally:
                # A recorder that raised part way through still appended what it
                # got to, and unlabelled signals are worse than missing ones.
                _stamp_device(segment, before, recorder.device_name)
        self.checkpoint_index += 1
        self._t_cursor = t_stop

        if self.part_filename is not None:
            from neo import io

            with io.NixIO(str(self.part_filename), mode="rw") as out:
                out._write_segment(segment, out.nix_file.blocks[self.block_key])
        else:
            self._block.segments.append(segment)

    def finalize(self) -> None:
        """
        Turn the per-rank parts into the one file the run was asked for.

        Every rank waits until all parts are written, then rank 0 merges them and
        removes the parts. A failed merge leaves them in place: they are the only
        copy of a completed run's results.
        """
        if self.filename is None or self.comm.get_size() == 1:
            return
        self.comm.barrier()
        try:
            if self.comm.get_rank() == 0:
                self._merge_parts()
        finally:
            # Every rank waits here for the merge, so rank 0 has to arrive whatever
            # the merge did. Leaving by an exception instead would hold the others on
            # this barrier for the rest of the run.
            self.comm.barrier()

    def _merge_parts(self) -> None:
        """
        Merge the parts on disk into ``filename``, and remove them.

        Only rank 0 runs this, between the two barriers of ``finalize``.
        """
        parts = [
            rank_part_path(self.filename, rank) for rank in range(self.comm.get_size())
        ]
        existing = [part for part in parts if part.exists()]
        if not existing:
            warn(
                f"No per-rank results were found for '{self.filename}'; the run "
                "wrote nothing to merge."
            )
            return
        try:
            merge_rank_results(existing, self.filename)
        except Exception:
            traceback.print_exc()
            warn(
                "Could not merge the per-rank results; they are kept at "
                f"'{existing[0].parent}' so the run is not lost."
            )
        else:
            shutil.rmtree(existing[0].parent, ignore_errors=True)

    def write(self, filename, mode="ow"):
        if self.filename is not None:
            shutil.copyfile(self.filename, filename)
        elif self.part_filename is not None:
            shutil.copyfile(self.part_filename, filename)
        else:
            from neo import io

            io.NixIO(str(filename), mode=mode).write(self._block)


class SimulationRecorder:
    def __init__(self, device=None):
        self.device = device

    @property
    def device_name(self):
        """The device this recorder belongs to, when it was created by one."""
        return getattr(self.device, "name", None)

    def flush(self, segment: "neo.core.Segment"):
        raise NotImplementedError("Recorders need to implement the `flush` function.")


@dataclasses.dataclass(frozen=True, eq=False)
class RecordedCell:
    """
    A cell of the network that a recording belongs to.
    """

    #: Id of the cell in the placement set of its cell model.
    id: int
    #: Name of the cell model the cell was simulated with.
    model: str
    #: The network's cell type that the cell model simulates.
    cell_type: "CellType"
    #: The placement set of that cell type.
    placement_set: "PlacementSet"
    #: Position of the cell, or ``None`` when its placement set stores no positions.
    position: "numpy.ndarray | None"


@dataclasses.dataclass(frozen=True)
class NetworkRecording(Recording):
    """
    A recording traced back to the network it was simulated on.
    """

    #: The cell the recording belongs to, or ``None`` for a device level record.
    cell: RecordedCell | None = None
    #: The run that made the recording.
    run: "SimulationRun | None" = None


class SimulationRun:
    """
    One run of a simulation in a results file, read with the network it ran on.

    Everything a run needs to trace its recordings back to the network is in its own
    block: the configuration it ran with names the cell type of each cell model.
    """

    def __init__(self, reader: "ResultsReader", block: "neo.core.Block"):
        self._reader = reader
        #: The Neo block holding the results of the run.
        self.block = block
        #: The configuration tree of the simulation, as it ran.
        self.configuration = read_simulation_config(block)
        #: The provenance of the run: its seed, duration, resolution, ranks, ...
        self.provenance = read_provenance(block)
        #: Names of the devices that recorded, in the order they were first written.
        self.devices = list(
            dict.fromkeys(
                recording.device
                for recording in iter_recordings(block)
                if recording.device is not None
            )
        )

    @property
    def name(self) -> str:
        """Name of the simulation that ran."""
        return self.block.name

    @property
    def run_index(self) -> int | None:
        """Which run of this simulation in the file it is, counting from ``0``."""
        return self.block.annotations.get("run_index")

    @property
    def simulation(self) -> "Simulation | None":
        """
        The network's simulation of this name, or ``None`` if the network has none.

        The network's configuration may have been changed since the run; the
        configuration the simulation ran with is :attr:`configuration`.
        """
        return self._reader.network.simulations.get(self.name)

    def recordings(
        self, device: str | None = None
    ) -> "typing.Iterator[NetworkRecording]":
        """
        Iterate the recordings of the run, each with the network's cell it belongs to.

        A device records every cell it targeted, so its recordings are all of its
        targets, including the cells that stayed silent.

        :param device: Only yield recordings made by this device.
        :returns: The recordings, in the order they were written.
        :rtype: typing.Iterator[NetworkRecording]
        """
        for recording in iter_recordings(self.block, device=device):
            yield NetworkRecording(
                device=recording.device,
                cell_id=recording.cell_id,
                cell_model=recording.cell_model,
                signal=recording.signal,
                cell=self._cell_of(recording),
                run=self,
            )

    def _cell_of(self, recording: Recording) -> RecordedCell | None:
        if recording.cell_id is None:
            return None
        if recording.cell_model is None:
            raise ResultsError(
                f"A recording of device '{recording.device}' names cell "
                f"{recording.cell_id} but not its cell model, so it cannot be traced "
                "back to the network. It was written before recordings named their "
                "cell model; read it with `iter_recordings` instead."
            )
        return self._reader._cell(
            self._cell_type_name(recording.cell_model),
            recording.cell_model,
            int(recording.cell_id),
            recording.device,
        )

    def _cell_type_name(self, model: str) -> str:
        """The name of the cell type a cell model simulated, as the run configured it."""
        tree = self.configuration if isinstance(self.configuration, dict) else {}
        models = tree.get("cell_models") or {}
        if model in models:
            # A cell model that does not name its cell type simulates the one of the
            # same name.
            return models[model].get("cell_type") or model
        simulation = self.simulation
        if simulation is not None and model in simulation.cell_models:
            return simulation.cell_models[model].cell_type.name
        raise ResultsError(
            f"Recordings name cell model '{model}', which simulation '{self.name}' "
            "does not have."
        )

    def __repr__(self):
        return f"<{type(self).__name__} '{self.name}' run {self.run_index}>"


class ResultsReader:
    """
    The results in a file, read together with the network they were simulated on.

    Made by :func:`read_results`, which verifies every run in the file against the
    network before handing one out.
    """

    def __init__(self, network: "Scaffold", blocks: "list[neo.core.Block]"):
        #: The network the simulations ran on.
        self.network = network
        #: The runs in the file, in the order they were written.
        self.runs = [SimulationRun(self, block) for block in blocks]
        # Loaded once per cell type and indexed into by every recording of it: a
        # device on a large population yields many thousands of recordings.
        self._placement = {}
        self._cells = {}

    @property
    def devices(self) -> list[str]:
        """Names of the devices that recorded, across the runs."""
        return list(dict.fromkeys(d for run in self.runs for d in run.devices))

    @property
    def simulation(self) -> "Simulation | None":
        """The network's simulation that ran, when the file holds a single run."""
        return self._only_run("simulation").simulation

    @property
    def configuration(self) -> dict | None:
        """The configuration of the simulation, when the file holds a single run."""
        return self._only_run("configuration").configuration

    @property
    def provenance(self) -> dict | None:
        """The provenance of the run, when the file holds a single run."""
        return self._only_run("provenance").provenance

    def _only_run(self, attr) -> SimulationRun:
        if len(self.runs) != 1:
            raise ResultsError(
                f"The file holds {len(self.runs)} runs, each with its own `{attr}`: "
                f"{', '.join(map(repr, self.runs))}. Read it from `runs`."
            )
        return self.runs[0]

    def recordings(
        self, device: str | None = None
    ) -> "typing.Iterator[NetworkRecording]":
        """
        Iterate the recordings of every run, each with the network's cell it belongs
        to, and the run that made it.

        :param device: Only yield recordings made by this device.
        :returns: The recordings, run by run, in the order they were written.
        :rtype: typing.Iterator[NetworkRecording]
        """
        for run in self.runs:
            yield from run.recordings(device)

    def _cell(self, type_name, model, cell_id, device) -> RecordedCell:
        key = (model, type_name, cell_id)
        try:
            return self._cells[key]
        except KeyError:
            pass
        cell_type, ps, positions, size = self._placement_of(type_name, model)
        if not 0 <= cell_id < size:
            raise ResultsError(
                f"A recording of device '{device}' names cell {cell_id} of cell model "
                f"'{model}', but the network holds {size} '{type_name}' cells. The "
                "placement changed after the run."
            )
        cell = self._cells[key] = RecordedCell(
            id=cell_id,
            model=model,
            cell_type=cell_type,
            placement_set=ps,
            position=None if positions is None else positions[cell_id],
        )
        return cell

    def _placement_of(self, type_name, model):
        try:
            return self._placement[type_name]
        except KeyError:
            pass
        try:
            cell_type = self.network.cell_types[type_name]
        except KeyError:
            raise ResultsError(
                f"Cell model '{model}' simulated cell type '{type_name}', which the "
                "network does not have."
            ) from None
        ps = cell_type.get_placement_set()
        try:
            positions = ps.load_positions()
        except DatasetNotFoundError:
            positions = None
            size = len(ps)
        else:
            size = len(positions)
        placement = self._placement[type_name] = (cell_type, ps, positions, size)
        return placement


def read_results(
    network: "str | os.PathLike | Scaffold", results: "str | os.PathLike"
) -> ResultsReader:
    """
    Read a results file together with the network it was simulated on.

    Every run in the file is verified before anything is returned. A run of another
    network raises a :class:`~bsb.exceptions.ResultsMismatchError`: analysed against
    the wrong network it would give plausible nonsense. A network that was written to
    after a run warns, because its positions or labels may have moved since, and a
    run that recorded no network identity warns that it cannot be verified.

    :param network: Path of the network file, or an opened network. A path is opened
        like :func:`~bsb.core.from_storage` opens it, which every rank of an MPI run
        takes part in: under MPI, read on every rank or pass an opened network.
    :param results: Path of the results file.
    :returns: A reader of the results, whose recordings name the network's cells.
    :raises ~bsb.exceptions.ResultsMismatchError: A run was not produced by this
        network.
    :raises ~bsb.exceptions.ResultsError: The file holds no results.
    """
    from neo import io

    from ..core import Scaffold
    from ..storage import open_storage

    with io.NixIO(str(results), mode="ro") as reader:
        blocks = reader.read_all_blocks()
    if not blocks:
        raise ResultsError(f"'{results}' holds no simulation results.")
    if isinstance(network, Scaffold):
        state_id = network.state_id
    else:
        storage = open_storage(str(network))
        # Loading a network stores its active configuration, which moves its state.
        # The state the results are verified against is the one it was found in.
        state_id = storage._engine.state_id
        network = storage.load()
    _verify_pairing(network, state_id, blocks, results)
    return ResultsReader(network, blocks)


def _verify_pairing(network, network_state_id, blocks, results):
    # Warned directly rather than through `bsb.reporting.warn`, which verbosity can
    # silence: a pairing that could not be verified is not diagnostic chatter. Each
    # concern warns once, however many runs share it.
    concerns = {}
    for block in blocks:
        recorded = ((read_provenance(block) or {}).get("scaffold")) or {}
        storage_id = recorded.get("storage_id")
        state_id = recorded.get("state_id")
        if storage_id is None or network.storage_id is None:
            concern = (
                "the run or the network carries no storage id, so they cannot be "
                "verified against each other"
            )
        elif storage_id != network.storage_id:
            raise ResultsMismatchError(
                f"Results of '{block.name}' in '{results}' were produced by network "
                f"'{storage_id}', not by network '{network.storage_id}'."
            )
        elif state_id is None or network_state_id is None:
            concern = (
                "the run or the network carries no state id, so the state of the "
                "network cannot be verified"
            )
        elif state_id != network_state_id:
            concern = (
                f"the network was written to after the run (state {state_id} then, "
                f"{network_state_id} now), so positions or labels may have changed "
                "since"
            )
        else:
            continue
        concerns.setdefault(concern, []).append(block.name)
    for concern, names in concerns.items():
        runs = ", ".join(f"'{name}'" for name in dict.fromkeys(names))
        warnings.warn(
            f"Results of {runs} in '{results}': {concern}.",
            ResultsWarning,
            stacklevel=3,
        )


__all__ = [
    "NetworkRecording",
    "RecordedCell",
    "Recording",
    "ResultsReader",
    "SimulationRun",
    "SimulationRecorder",
    "SimulationResult",
    "iter_recordings",
    "merge_rank_results",
    "rank_part_path",
    "read_provenance",
    "read_results",
    "read_simulation_config",
]
