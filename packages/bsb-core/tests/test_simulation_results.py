import pathlib
import tempfile
import unittest

import numpy as np
from neo import Block, Segment, SpikeTrain
from neo import io as neo_io
from quantities import ms

from bsb.services import MPI
from bsb.simulation.results import (
    SimulationResult,
    iter_recordings,
    merge_rank_results,
    rank_part_path,
    read_provenance,
    read_simulation_config,
    silent_cells,
)
from bsb.storage.provenance import SCHEMA_VERSION, encode_annotation


def _part(path, simulation_id, checkpoints, rank):
    """Write one rank's share of a run: a block whose segments carry its spikes."""
    block = Block(name="sim")
    block.annotate(bsb_simulation_id=simulation_id)
    for index, times in enumerate(checkpoints):
        segment = Segment()
        segment.annotate(
            segment_id=f"{simulation_id}:{index}",
            checkpoint_index=index,
            mpi_rank=rank,
        )
        segment.spiketrains.append(
            SpikeTrain(np.asarray(times) * ms, t_stop=100 * ms, mpi_rank=rank)
        )
        block.segments.append(segment)
    with neo_io.NixIO(str(path), mode="ow") as out:
        out.write_block(block)


class TestRankParts(unittest.TestCase):
    """A run ends with one file, whatever it took to produce it."""

    def setUp(self):
        self.dir = pathlib.Path(tempfile.mkdtemp())
        self.final = self.dir / "results.nio"

    def test_parts_live_beside_the_file_they_become(self):
        part = rank_part_path(self.final, 2)

        self.assertEqual("rank2.nio", part.name)
        self.assertEqual(self.dir, part.parent.parent, "parts sit beside the result")
        self.assertNotEqual(self.final, part, "a part is never the finished file")

    def test_every_rank_gets_its_own_part(self):
        parts = {rank_part_path(self.final, rank) for rank in range(4)}

        self.assertEqual(4, len(parts), "ranks must not write to the same path")

    def test_merging_concatenates_what_each_rank_recorded(self):
        # Ranks record disjoint cells, so the merge is a concatenation: every
        # recording survives and none is reconciled away.
        sid = "run-1"
        first, second = self.dir / "r0.nio", self.dir / "r1.nio"
        _part(first, sid, [[1.0, 2.0], [5.0]], rank=0)
        _part(second, sid, [[3.0], [6.0, 7.0]], rank=1)

        merge_rank_results([first, second], self.final)

        block = neo_io.NixIO(str(self.final), "ro").read_all_blocks()[0]
        self.assertEqual(2, len(block.segments), "checkpoints must not multiply")
        counts = [len(segment.spiketrains) for segment in block.segments]
        self.assertEqual([2, 2], counts, "each rank's train is kept")
        spikes = sorted(
            float(t) for train in block.segments[0].spiketrains for t in train
        )
        self.assertEqual([1.0, 2.0, 3.0], spikes)

    def test_segments_line_up_on_their_checkpoint(self):
        # Ranks can flush a different number of times; a segment only merges into
        # the one that covers the same window.
        sid = "run-2"
        first, second = self.dir / "r0.nio", self.dir / "r1.nio"
        _part(first, sid, [[1.0], [2.0], [3.0]], rank=0)
        _part(second, sid, [[4.0]], rank=1)

        merge_rank_results([first, second], self.final)

        block = neo_io.NixIO(str(self.final), "ro").read_all_blocks()[0]
        self.assertEqual(3, len(block.segments))
        self.assertEqual(2, len(block.segments[0].spiketrains), "checkpoint 0 merged")
        self.assertEqual(1, len(block.segments[1].spiketrains), "checkpoint 1 alone")

    def test_which_rank_recorded_a_train_survives_the_merge(self):
        # The merge collapses the files, so rank is recorded per object or it is lost.
        sid = "run-3"
        first, second = self.dir / "r0.nio", self.dir / "r1.nio"
        _part(first, sid, [[1.0]], rank=0)
        _part(second, sid, [[2.0]], rank=1)

        merge_rank_results([first, second], self.final)

        block = neo_io.NixIO(str(self.final), "ro").read_all_blocks()[0]
        ranks = sorted(
            train.annotations["mpi_rank"] for train in block.segments[0].spiketrains
        )
        self.assertEqual([0, 1], ranks)


class TestProvenanceReading(unittest.TestCase):
    """Reading a results file back, including one written by another BSB."""

    def test_a_bundle_round_trips(self):
        bundle = {"schema_version": SCHEMA_VERSION, "simulation_id": "abc"}
        block = Block(name="sim")
        block.annotate(bsb_provenance=encode_annotation(bundle))

        self.assertEqual(bundle, read_provenance(block))

    def test_a_block_without_provenance_reads_as_none(self):
        self.assertIsNone(read_provenance(Block(name="sim")))

    def test_a_newer_schema_warns_and_degrades(self):
        # The recordings are plain neo and readable regardless, so refusing the file
        # over its metadata would keep someone from intact results.
        import warnings

        block = Block(name="sim")
        block.annotate(
            bsb_provenance=encode_annotation(
                {"schema_version": SCHEMA_VERSION + 1, "simulation_id": "abc"}
            )
        )

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            bundle = read_provenance(block)

        self.assertEqual("abc", bundle["simulation_id"], "what is readable is read")
        self.assertTrue(any("newer" in str(w.message) for w in caught))

    def test_a_block_without_a_configuration_reads_as_none(self):
        self.assertIsNone(read_simulation_config(Block(name="sim")))



class _Result(SimulationResult):
    """
    A result standing in for a run.

    Built without a simulation or a file, so the annotation helpers can be asked
    directly rather than through a whole prepared simulation.
    """

    def __init__(self):
        self.comm = MPI
        self.simulation_id = "run-x"
        self.checkpoint_index = 3
        self._device_targets = {}


class _Device:
    name = "my_recorder"


class TestRecorderConvention(unittest.TestCase):
    """What every recorded object says about where it came from."""

    def setUp(self):
        self.result = _Result()

    def test_a_spike_train_says_where_it_came_from(self):
        train = self.result.spike_train(
            times=[1.0, 2.0],
            device=_Device(),
            t_stop=100.0,
            ps_name="granule",
            cell_id=7,
            cell_model="granule_model",
        )

        a = train.annotations
        self.assertEqual("my_recorder", a["bsb_device_name"])
        self.assertEqual("cell", a["bsb_recording_kind"])
        self.assertEqual("record", a["bsb_direction"], "recorders record by default")
        self.assertEqual("granule", a["bsb_ps_name"])
        self.assertEqual(7, a["bsb_cell_id"])
        self.assertEqual("run-x:3", a["bsb_segment_id"], "which flush it belongs to")
        self.assertIn("bsb_mpi_rank", a, "rank must survive the merge")

    def test_a_stimulator_is_a_direction_not_a_kind(self):
        # A stimulator addresses the same things a recorder does, with the data
        # flowing the other way.
        train = self.result.spike_train(
            times=[1.0], device=_Device(), t_stop=10.0, direction="stimulate"
        )

        self.assertEqual("stimulate", train.annotations["bsb_direction"])
        self.assertEqual("cell", train.annotations["bsb_recording_kind"])

    def test_a_point_recording_addresses_the_morphology(self):
        signal = self.result.analog_signal(
            data=[0.1, 0.2],
            units="mV",
            sampling_period=1.0 * ms,
            device=_Device(),
            name="v",
            ps_name="purkinje",
            cell_id=2,
            recording_kind="point",
            branch=4,
            point=11,
            arc=0.5,
        )

        a = signal.annotations
        self.assertEqual("point", a["bsb_recording_kind"], "never 'compartment'")
        self.assertEqual(4, a["bsb_branch"])
        self.assertEqual(11, a["bsb_point"])
        self.assertEqual(0.5, a["bsb_arc"])

    def test_annotations_are_flat_scalars(self):
        # Flat values survive a write without encoding and stay queryable in the
        # file; a nested one would reach the file as its keys alone.
        train = self.result.spike_train(
            times=[1.0], device=_Device(), t_stop=10.0, ps_name="granule", cell_id=1
        )

        for key, value in train.annotations.items():
            if key.startswith("bsb_"):
                with self.subTest(annotation=key):
                    self.assertNotIsInstance(value, dict | list)

    def test_targets_are_recorded_so_silence_stays_recoverable(self):
        # A recorder emits nothing for a silent cell, so what was targeted is what
        # makes the difference recoverable.
        device = _Device()
        self.result.record_device_targets(device, {"granule": [0, 1, 2]})

        self.assertEqual(
            {"my_recorder": {"granule": [0, 1, 2]}}, self.result._device_targets
        )


class TestReaderSurface(unittest.TestCase):
    """Finding things in a results file."""

    def setUp(self):
        self.result = _Result()
        self.block = Block(name="sim")
        segment = Segment()
        device = _Device()
        segment.spiketrains.extend(
            [
                self.result.spike_train(
                    times=[1.0],
                    device=device,
                    t_stop=10.0,
                    ps_name="granule",
                    cell_id=0,
                ),
                self.result.spike_train(
                    times=[2.0],
                    device=device,
                    t_stop=10.0,
                    ps_name="granule",
                    cell_id=2,
                ),
                # A stimulator: no cell of its own, but it followed the convention.
                self.result.spike_train(
                    times=[3.0], device=device, t_stop=10.0, direction="stimulate"
                ),
                # Something that ignored the convention entirely.
                SpikeTrain([4.0] * ms, t_stop=10 * ms),
            ]
        )
        self.block.segments.append(segment)
        self.result.record_device_targets(device, {"granule": [0, 1, 2, 3]})
        self.block.annotate(
            bsb_provenance=encode_annotation(
                {"schema_version": SCHEMA_VERSION, "devices": self.result._device_targets}
            )
        )

    def test_everything_is_walked_including_what_ignored_the_convention(self):
        # Dropping unannotated objects would hide a plugin's output entirely.
        self.assertEqual(4, len(list(iter_recordings(self.block))))

    def test_a_stimulator_is_not_dropped_for_having_no_cell(self):
        stimuli = [
            r for r in iter_recordings(self.block) if r.direction == "stimulate"
        ]

        self.assertEqual(1, len(stimuli))
        self.assertIsNone(stimuli[0].ps_name, "a stimulator addresses no cell of its own")

    def test_filtering_matches_on_annotations(self):
        granule = list(iter_recordings(self.block, ps_name="granule"))

        self.assertEqual(2, len(granule))
        self.assertEqual([0, 2], sorted(r.cell_id for r in granule))

    def test_silence_is_the_difference_between_targeted_and_recorded(self):
        # Cells 0 and 2 spiked; 1 and 3 were watched and stayed silent.
        self.assertEqual(
            {"granule": [1, 3]}, silent_cells(self.block, "my_recorder")
        )


if __name__ == "__main__":
    unittest.main()
