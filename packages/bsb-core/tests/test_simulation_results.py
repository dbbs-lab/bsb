import pathlib
import tempfile
import unittest

import numpy as np
from neo import Block, Segment, SpikeTrain
from neo import io as neo_io
from quantities import ms

from bsb.simulation.results import (
    merge_rank_results,
    rank_part_path,
    read_provenance,
    read_simulation_config,
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


if __name__ == "__main__":
    unittest.main()
