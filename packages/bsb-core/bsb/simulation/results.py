import pathlib
import shutil
import traceback
import typing
import uuid
from datetime import datetime

from ..reporting import warn
from ..services import MPI
from ..storage.provenance import (
    SCHEMA_VERSION,
    collect_host_info,
    collect_plugin_manifest,
    decode_annotation,
    encode_annotation,
    iso_now,
)

if typing.TYPE_CHECKING:  # pragma: nocover
    import neo


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
    if version is not None and version > SCHEMA_VERSION:
        warn(
            f"Results of '{block.name}' were written with provenance schema "
            f"{version}, newer than this BSB's {SCHEMA_VERSION}. Reading what is "
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
    ``checkpoint_index``, which is what makes them line up across parts.

    :param parts: The per-rank files, in rank order.
    :param filename: The file to write.
    """
    from neo import io

    merged = {}
    order = []
    for part in parts:
        for block in io.NixIO(str(part), "ro").read_all_blocks():
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
            out.write_block(merged[key])


class SimulationResult:
    """
    The results of one simulation, and the provenance of the run that made them.

    Under MPI each rank writes its own part and rank 0 merges them into the file
    that was asked for, because neither ``nixio`` nor an HDF5 attribute supports
    concurrent writers. The parts are an implementation detail: a run ends with one
    file, and :meth:`finalize` is what makes that true.
    """

    def __init__(self, simulation, filename=None, comm=None):
        from neo import Block

        self.comm = comm or MPI
        self.simulation = simulation
        self.recorders = []
        self.checkpoint_index = 0
        self._t_cursor = 0.0

        # One identity for the whole run, agreed by every rank. Drawn on rank 0 and
        # broadcast: drawn per rank, the parts of one run could not be recognised as
        # belonging together.
        self.simulation_id = self.comm.bcast(str(uuid.uuid4()), root=0)

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
            "schema_version": SCHEMA_VERSION,
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
            try:
                recorder.flush(segment)
            except Exception:
                traceback.print_exc()
                warn("Recorder errored out!")
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
        if self.comm.get_rank() == 0:
            parts = [
                rank_part_path(self.filename, rank)
                for rank in range(self.comm.get_size())
            ]
            existing = [part for part in parts if part.exists()]
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
        self.comm.barrier()

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


__all__ = [
    "SimulationRecorder",
    "SimulationResult",
    "merge_rank_results",
    "rank_part_path",
    "read_provenance",
    "read_simulation_config",
]
