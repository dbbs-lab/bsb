import dataclasses
import functools
import pathlib
import shutil
import traceback
import typing
import uuid
import warnings
from datetime import datetime

import numpy as np

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
    import scipy.spatial.transform

    from ..cell_types import CellType
    from ..core import Scaffold
    from ..morphologies import Morphology
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


#: The kinds of target a recording can have. The set is closed: a recording of any
#: other kind cannot be traced back to anything, which is warned about.
_KINDS = ("cell", "point", "synapse", "device")
#: The directions a recording can have.
_DIRECTIONS = ("record", "stimulate")


def _warn_unlabelled(segment, before: dict, recorder) -> None:
    """
    Warn about what a recorder just appended without saying what it recorded.

    Every recording should carry one of the recording kinds and a direction, or it
    cannot be traced back to what it recorded once it is in a file. It is still
    written, so no data is lost, and it is warned about rather than raised on:
    recorders flush during a run, on every rank on its own, and a rank that raised
    there would leave the others waiting.
    """
    for name in _RECORDING_LISTS:
        for recording in getattr(segment, name)[before[name] :]:
            annotations = recording.annotations
            missing = [
                key
                for key, valid in (
                    (
                        "bsb_recording_kind",
                        annotations.get("bsb_recording_kind") in _KINDS,
                    ),
                    ("bsb_direction", annotations.get("bsb_direction") in _DIRECTIONS),
                )
                if not valid
            ]
            if missing:
                warnings.warn(
                    f"Device '{recorder.device_name}' recorded a signal without a valid "
                    f"{' or '.join(f'`{key}`' for key in missing)}, so it cannot be "
                    "traced back to what it recorded. "
                    "Annotate recordings with `cell_annotations`, `point_annotations`, "
                    "`synapse_annotations` or `device_annotations`.",
                    ResultsWarning,
                    stacklevel=2,
                )


def _stamp_baseline(segment, before: dict, recorder, simulation_id, segment_id) -> None:
    """
    Annotate what a recorder just appended with the baseline every recording carries.

    The baseline is stamped here rather than by each recorder so that every backend
    answers "which device and which run produced this?" the same way, without every
    device author having to remember to say so. A recorder that already set one of
    these keeps its own answer.
    """
    baseline = {
        "bsb_device_name": recorder.device_name,
        "bsb_device_kind": recorder.device_kind,
        "bsb_simulation_id": simulation_id,
        "bsb_segment_id": segment_id,
    }
    baseline = {key: value for key, value in baseline.items() if value is not None}
    for name in _RECORDING_LISTS:
        recordings = getattr(segment, name)
        for recording in recordings[before[name] :]:
            for key, value in baseline.items():
                recording.annotations.setdefault(key, value)


def device_annotations(direction: str) -> dict:
    """
    Annotations of a recording of the device itself, which addresses nothing in the
    network: a signal the device computes, rather than one it takes from a cell.

    :param direction: ``"record"`` when the device observes what it records, or
      ``"stimulate"`` when it injects it.
    :returns: The annotations to pass to the Neo object.
    """
    return {"bsb_recording_kind": "device", "bsb_direction": direction}


def cell_annotations(cell_model, cell_id: int, direction: str) -> dict:
    """
    Annotations of a recording of a whole cell.

    :param cell_model: The cell model the cell was simulated with.
    :type cell_model: ~bsb.simulation.cell.CellModel
    :param cell_id: Id of the cell in the placement set of the cell model's cell type.
    :param direction: ``"record"`` when the device observes what it records, or
      ``"stimulate"`` when it injects it.
    :returns: The annotations to pass to the Neo object.
    """
    return {
        "bsb_recording_kind": "cell",
        "bsb_direction": direction,
        "bsb_ps_name": cell_model.cell_type.name,
        "bsb_cell_model": cell_model.name,
        "bsb_cell_id": int(cell_id),
    }


def point_annotations(
    cell_model, cell_id: int, branch: int, point: int, arc: float, direction: str
) -> dict:
    """
    Annotations of a recording at a point on a cell's morphology.

    :param cell_model: The cell model the cell was simulated with.
    :type cell_model: ~bsb.simulation.cell.CellModel
    :param cell_id: Id of the cell in the placement set of the cell model's cell type.
    :param branch: Index of the branch in the cell's morphology.
    :param point: Index of the point on that branch.
    :param arc: Where on the stretch following that point the recording is, as a
      fraction of the branch's length.
    :param direction: ``"record"`` when the device observes what it records, or
      ``"stimulate"`` when it injects it.
    :returns: The annotations to pass to the Neo object.
    """
    return {
        **cell_annotations(cell_model, cell_id, direction),
        "bsb_recording_kind": "point",
        "bsb_branch": int(branch),
        "bsb_point": int(point),
        "bsb_arc": float(arc),
    }


def synapse_annotations(
    post, synapse_type: str, direction: str, pre=None, connectivity_set=None
) -> dict:
    """
    Annotations of a recording of a synapse, between the cell it is on and the cell of
    the connection it belongs to.

    :param post: Where the synapse is: the cell model, cell id, branch, point, and arc
      of the location on the postsynaptic cell.
    :type post: tuple[~bsb.simulation.cell.CellModel, int, int, int, float]
    :param synapse_type: Name of the synapse type.
    :param direction: ``"record"`` when the device observes what it records, or
      ``"stimulate"`` when it injects it.
    :param pre: Where the connection starts: the cell model, cell id, branch and point
      of the location on the presynaptic cell. ``None`` for a synapse that belongs to
      no connection.
    :type pre: tuple[~bsb.simulation.cell.CellModel, int, int, int] | None
    :param connectivity_set: Name of the connectivity set of the connection.
    :returns: The annotations to pass to the Neo object.
    """
    post_model, post_id, post_branch, post_point, post_arc = post
    annotations = {
        "bsb_recording_kind": "synapse",
        "bsb_direction": direction,
        "bsb_synapse_type": synapse_type,
        **_hemitype("post", post_model, post_id, post_branch, post_point),
        "bsb_post_arc": float(post_arc),
    }
    if pre is not None:
        annotations.update(_hemitype("pre", *pre))
    if connectivity_set is not None:
        annotations["bsb_connectivity_set"] = connectivity_set
    return annotations


def _hemitype(side, cell_model, cell_id, branch, point):
    return {
        f"bsb_{side}_ps_name": cell_model.cell_type.name,
        f"bsb_{side}_cell_model": cell_model.name,
        f"bsb_{side}_cell_id": int(cell_id),
        f"bsb_{side}_branch": int(branch),
        f"bsb_{side}_point": int(point),
    }


@dataclasses.dataclass(frozen=True)
class Recording:
    """
    One recorded Neo object and what it says about itself.

    Every recording names the device that made it, what kind of thing it recorded,
    and whether the device observed it or injected it, whatever backend ran the
    simulation and whichever Neo container it landed in. What it recorded is
    addressed by the annotations of its kind, never by a simulator's own ids.
    """

    #: Name of the device that produced the recording.
    device: str | None
    #: What kind of thing was recorded: ``cell``, ``point``, ``synapse`` or ``device``.
    kind: str | None
    #: ``"record"`` when the device observed it, or ``"stimulate"`` when it injected it.
    direction: str | None
    #: The Neo object itself, a ``SpikeTrain`` or an ``AnalogSignal``.
    signal: typing.Any

    @property
    def annotations(self) -> dict:
        """All annotations of the Neo object, including those of its kind."""
        return self.signal.annotations

    @property
    def is_spike_train(self) -> bool:
        return type(self.signal).__name__ == "SpikeTrain"


def iter_recordings(
    source,
    device: str | None = None,
    kind: str | None = None,
    cell_model: str | None = None,
    cell_id: int | None = None,
) -> "typing.Iterator[Recording]":
    """
    Iterate the recordings of a block, a segment, or a list of either.

    :param source: What to read: a :class:`neo.core.Block`, a
        :class:`neo.core.Segment`, or an iterable of either.
    :param device: Only yield recordings made by this device.
    :param kind: Only yield recordings of this kind.
    :param cell_model: Only yield recordings on cells of this cell model. A
        synapse is on its postsynaptic cell.
    :param cell_id: Only yield recordings on cells with this id. A cell id is only
        unique within its cell model, so pass ``cell_model`` along to single out one
        cell.
    :returns: The recordings, in the order they were written.
    :rtype: typing.Iterator[Recording]
    """
    for segment in _iter_segments(source):
        for name in _RECORDING_LISTS:
            for signal in getattr(segment, name, ()):
                annotations = signal.annotations
                if device is not None and annotations.get("bsb_device_name") != device:
                    continue
                if kind is not None and annotations.get("bsb_recording_kind") != kind:
                    continue
                if (
                    cell_model is not None
                    and _on_cell(annotations, "cell_model") != cell_model
                ):
                    continue
                if cell_id is not None and _on_cell(annotations, "cell_id") != cell_id:
                    continue
                yield Recording(
                    device=annotations.get("bsb_device_name"),
                    kind=annotations.get("bsb_recording_kind"),
                    direction=annotations.get("bsb_direction"),
                    signal=signal,
                )


def _on_cell(annotations, key):
    """
    An annotation of the cell a recording is on: the recorded cell, or the cell a
    recorded synapse is on.
    """
    value = annotations.get(f"bsb_{key}")
    return annotations.get(f"bsb_post_{key}") if value is None else value


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
        """
        Add a recorder, which every checkpoint asks to flush what it recorded.

        :param recorder: The recorder. It has to belong to a device, which is what
          every one of its recordings names as the device that made it.
        :type recorder: SimulationRecorder
        """
        if getattr(recorder, "device", None) is None:
            raise ResultsError(
                f"Recorder {recorder!r} belongs to no device. Every recording names "
                "the device that made it, so a recorder has to be created by one."
            )
        self.recorders.append(recorder)

    def create_recorder(self, flush: typing.Callable[["neo.core.Segment"], None], device):
        """
        Add a recorder that flushes with a function.

        :param flush: Appends what was recorded since the last checkpoint to the
          segment it is given, annotated with what it recorded.
        :param device: The device the recordings belong to.
        :returns: The recorder.
        :rtype: SimulationRecorder
        """
        recorder = SimulationRecorder(device=device)
        recorder.flush = flush
        self.add(recorder)
        return recorder

    def flush(self):
        from neo import Segment

        segment = Segment()
        t_stop = float(getattr(self.simulation, "duration", 0.0) or 0.0)
        # Segments of one run are matched across rank files by this, so it is derived
        # rather than drawn: a per-rank id would never line up.
        segment_id = f"{self.simulation_id}:{self.checkpoint_index}"
        segment.annotate(
            segment_id=segment_id,
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
                _warn_unlabelled(segment, before, recorder)
                _stamp_baseline(segment, before, recorder, self.simulation_id, segment_id)
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
    def __init__(self, device):
        self.device = device

    @property
    def device_name(self):
        """The name of the device this recorder belongs to."""
        return getattr(self.device, "name", None)

    @property
    def device_kind(self):
        """The kind of device this recorder belongs to, as it is configured."""
        return getattr(self.device, "device", None)

    def flush(self, segment: "neo.core.Segment"):
        raise NotImplementedError("Recorders need to implement the `flush` function.")


class _Placement:
    """
    What a reader loads of one placement set, once, for every recording on its cells.

    Positions are loaded up front, because every recorded cell has one. Morphologies
    and rotations are only loaded once a recording asks for them.
    """

    def __init__(self, cell_type):
        self.cell_type = cell_type
        self.placement_set = cell_type.get_placement_set()
        try:
            self.positions = self.placement_set.load_positions()
        except DatasetNotFoundError:
            self.positions = None
            self.size = len(self.placement_set)
        else:
            self.size = len(self.positions)

    @functools.cached_property
    def morphologies(self):
        try:
            return self.placement_set.load_morphologies()
        except DatasetNotFoundError:
            return None

    @functools.cached_property
    def rotations(self):
        try:
            return self.placement_set.load_rotations()
        except DatasetNotFoundError:
            return None


@dataclasses.dataclass(frozen=True, eq=False)
class RecordedCell:
    """
    A cell of the network, as a recording addresses it.
    """

    #: Id of the cell in the placement set of its cell type.
    id: int
    #: Name of the cell model the cell was simulated with.
    model: str
    # What the reader loaded of the cell's placement set, shared by its cells.
    _placement: typing.Any = dataclasses.field(repr=False)

    @property
    def cell_type(self) -> "CellType":
        """The network's cell type of the cell."""
        return self._placement.cell_type

    @property
    def placement_set(self) -> "PlacementSet":
        """The placement set of that cell type."""
        return self._placement.placement_set

    @property
    def position(self) -> "numpy.ndarray | None":
        """Position of the cell, or ``None`` when its placement set stores none."""
        positions = self._placement.positions
        return None if positions is None else positions[self.id]

    @property
    def morphology(self) -> "Morphology | None":
        """
        The morphology of the cell as it is in the network: rotated by the cell's
        rotation and moved to its position. A copy, so changing it changes nothing in
        the network. ``None`` when its placement set stores no morphologies.
        """
        morphologies = self._placement.morphologies
        if morphologies is None:
            return None
        morphology = morphologies.get(self.id)
        rotation = self.rotation
        if rotation is not None:
            morphology.rotate(rotation)
        position = self.position
        if position is not None:
            morphology.translate(position)
        return morphology

    @property
    def rotation(self) -> "scipy.spatial.transform.Rotation | None":
        """
        The rotation of the cell's morphology in the network, or ``None`` when its
        placement set stores no rotations.
        """
        rotations = self._placement.rotations
        return None if rotations is None else rotations[self.id]

    def _position_on(
        self, branch: int, point: int, arc: float | None
    ) -> "numpy.ndarray | None":
        """Where a location on the morphology is, in the network."""
        morphologies = self._placement.morphologies
        position = self.position
        if morphologies is None or position is None:
            return None
        # The stored morphology, shared with every other recording on a cell of it and
        # only read here, is placed one location at a time rather than copied and
        # placed whole for every recording.
        morphology = morphologies.get(self.id, hard_cache=True)
        try:
            points = morphology.branches[branch].points
        except IndexError:
            raise ResultsError(
                f"Cell {self.id} of '{self.cell_type.name}' is recorded on branch "
                f"{branch}, but its morphology has {len(morphology.branches)} branches."
            ) from None
        if arc is None:
            try:
                local = points[point]
            except IndexError:
                raise ResultsError(
                    f"Cell {self.id} of '{self.cell_type.name}' is recorded on point "
                    f"{point} of branch {branch}, which has {len(points)} points."
                ) from None
        else:
            lengths = np.concatenate(
                ([0.0], np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1)))
            )
            local = np.array(
                [
                    np.interp(arc * lengths[-1], lengths, points[:, axis])
                    for axis in range(3)
                ]
            )
        rotation = self.rotation
        if rotation is not None:
            local = rotation.apply(local)
        return local + position


@dataclasses.dataclass(frozen=True, eq=False)
class RecordedPoint:
    """
    A point on the morphology of a cell of the network, as a recording addresses it.
    """

    #: The cell the point is on.
    cell: RecordedCell
    #: Index of the branch in the cell's morphology.
    branch: int
    #: Index of the point on that branch.
    point: int
    #: Where on the branch, as a fraction of the branch's length, or ``None`` when the
    #: location is the point itself.
    arc: float | None = None

    @property
    def position(self) -> "numpy.ndarray | None":
        """
        Where the location is in the network, on the cell's morphology as the cell is
        placed. ``None`` when the network stores no morphologies or positions for the
        cell.
        """
        return self.cell._position_on(self.branch, self.point, self.arc)


@dataclasses.dataclass(frozen=True, eq=False)
class RecordedSynapse:
    """
    A synapse between two cells of the network, as a recording addresses it.
    """

    #: Where the synapse is on its postsynaptic cell.
    post: RecordedPoint
    #: Where the connection the synapse belongs to starts on its presynaptic cell, or
    #: ``None`` for a synapse that belongs to no connection.
    pre: RecordedPoint | None
    #: Name of the synapse type.
    synapse_type: str
    #: Name of the connectivity set of the connection, if any.
    connectivity_set: str | None

    @property
    def position(self) -> "numpy.ndarray | None":
        """Where the synapse is in the network: its location on the postsynaptic cell."""
        return self.post.position


@dataclasses.dataclass(frozen=True, eq=False)
class RecordedDevice:
    """
    The device a recording of the device itself belongs to.
    """

    #: Name of the device.
    name: str
    #: The kind of device, as configured.
    kind: str | None
    #: The configuration of the device, as the simulation ran with it, or ``None`` if
    #: the run recorded no configuration.
    configuration: dict | None


@dataclasses.dataclass(frozen=True)
class NetworkRecording(Recording):
    """
    A recording traced back to the network it was simulated on.
    """

    #: What was recorded: a :class:`RecordedCell`, :class:`RecordedPoint`,
    #: :class:`RecordedSynapse` or :class:`RecordedDevice`, depending on the
    #: recording's :attr:`~Recording.kind`. ``None`` for a kind this BSB does not know.
    target: "RecordedCell | RecordedPoint | RecordedSynapse | RecordedDevice | None" = (
        None
    )
    #: The run that made the recording.
    run: "SimulationRun | None" = None


class SimulationRun:
    """
    One run of a simulation in a results file, read with the network it ran on.
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
        self, device: str | None = None, kind: str | None = None
    ) -> "typing.Iterator[NetworkRecording]":
        """
        Iterate the recordings of the run, each with what it recorded in the network.

        :param device: Only yield recordings made by this device.
        :param kind: Only yield recordings of this kind.
        :returns: The recordings, in the order they were written.
        :rtype: typing.Iterator[NetworkRecording]
        """
        for recording in iter_recordings(self.block, device=device, kind=kind):
            yield NetworkRecording(
                device=recording.device,
                kind=recording.kind,
                direction=recording.direction,
                signal=recording.signal,
                target=self._reader._target(recording, self),
                run=self,
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
        # Recordings that cannot be traced are warned about once per device and kind,
        # not once per recording.
        self._untraceable = set()

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
        self, device: str | None = None, kind: str | None = None
    ) -> "typing.Iterator[NetworkRecording]":
        """
        Iterate the recordings of every run, each with what it recorded in the
        network, and the run that made it.

        :param device: Only yield recordings made by this device.
        :param kind: Only yield recordings of this kind.
        :returns: The recordings, run by run, in the order they were written.
        :rtype: typing.Iterator[NetworkRecording]
        """
        for run in self.runs:
            yield from run.recordings(device, kind)

    def _target(self, recording: Recording, run: SimulationRun):
        annotations = recording.annotations
        kind = recording.kind
        if kind == "device":
            configuration = run.configuration
            devices = (
                configuration.get("devices") if isinstance(configuration, dict) else None
            )
            return RecordedDevice(
                name=recording.device,
                kind=annotations.get("bsb_device_kind"),
                configuration=(devices or {}).get(recording.device),
            )
        if kind == "cell":
            return self._cell(recording, "")
        if kind == "point":
            return RecordedPoint(
                cell=self._cell(recording, ""),
                branch=int(self._field(recording, "bsb_branch")),
                point=int(self._field(recording, "bsb_point")),
                arc=float(self._field(recording, "bsb_arc")),
            )
        if kind == "synapse":
            return RecordedSynapse(
                post=RecordedPoint(
                    cell=self._cell(recording, "post_"),
                    branch=int(self._field(recording, "bsb_post_branch")),
                    point=int(self._field(recording, "bsb_post_point")),
                    arc=float(self._field(recording, "bsb_post_arc")),
                ),
                pre=(
                    RecordedPoint(
                        cell=self._cell(recording, "pre_"),
                        branch=int(self._field(recording, "bsb_pre_branch")),
                        point=int(self._field(recording, "bsb_pre_point")),
                    )
                    if "bsb_pre_cell_id" in annotations
                    else None
                ),
                synapse_type=self._field(recording, "bsb_synapse_type"),
                connectivity_set=annotations.get("bsb_connectivity_set"),
            )
        if (recording.device, kind) not in self._untraceable:
            self._untraceable.add((recording.device, kind))
            described = (
                "no recording kind" if kind is None else f"recording kind '{kind}'"
            )
            warnings.warn(
                f"Recordings of device '{recording.device}' in run '{run.name}' have "
                f"{described}, which this version of the BSB cannot trace back to "
                "what they recorded; their `target` is `None`.",
                ResultsWarning,
                stacklevel=4,
            )
        return None

    @staticmethod
    def _field(recording, key):
        try:
            return recording.annotations[key]
        except KeyError:
            raise ResultsError(
                f"A '{recording.kind}' recording of device '{recording.device}' is "
                f"missing its `{key}` annotation."
            ) from None

    def _cell(self, recording, prefix) -> RecordedCell:
        ps_name = self._field(recording, f"bsb_{prefix}ps_name")
        model = self._field(recording, f"bsb_{prefix}cell_model")
        cell_id = int(self._field(recording, f"bsb_{prefix}cell_id"))
        key = (ps_name, model, cell_id)
        try:
            return self._cells[key]
        except KeyError:
            pass
        placement = self._placement_of(ps_name)
        if not 0 <= cell_id < placement.size:
            raise ResultsError(
                f"A recording of device '{recording.device}' names cell {cell_id} of "
                f"'{ps_name}', but the network holds {placement.size} '{ps_name}' "
                "cells. The placement changed after the run."
            )
        cell = self._cells[key] = RecordedCell(cell_id, model, placement)
        return cell

    def _placement_of(self, ps_name):
        try:
            return self._placement[ps_name]
        except KeyError:
            pass
        try:
            cell_type = self.network.cell_types[ps_name]
        except KeyError:
            raise ResultsError(
                f"Recordings name cells of '{ps_name}', which the network does not have."
            ) from None
        placement = self._placement[ps_name] = _Placement(cell_type)
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

    from ..core import Scaffold, from_storage

    with io.NixIO(str(results), mode="ro") as reader:
        blocks = reader.read_all_blocks()
    if not blocks:
        raise ResultsError(f"'{results}' holds no simulation results.")
    if not isinstance(network, Scaffold):
        network = from_storage(str(network))
    _verify_pairing(network, blocks, results)
    return ResultsReader(network, blocks)


def _verify_pairing(network, blocks, results):
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
        elif state_id is None or network.state_id is None:
            concern = (
                "the run or the network carries no state id, so the state of the "
                "network cannot be verified"
            )
        elif state_id != network.state_id:
            concern = (
                f"the network was written to after the run (state {state_id} then, "
                f"{network.state_id} now), so positions or labels may have changed "
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
    "RecordedPoint",
    "RecordedDevice",
    "RecordedSynapse",
    "Recording",
    "ResultsReader",
    "SimulationRun",
    "SimulationRecorder",
    "SimulationResult",
    "cell_annotations",
    "device_annotations",
    "iter_recordings",
    "merge_rank_results",
    "point_annotations",
    "rank_part_path",
    "read_provenance",
    "read_results",
    "read_simulation_config",
    "synapse_annotations",
]
