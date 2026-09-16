import pathlib
import shutil
import tempfile
import types
import unittest

import numpy as np
from bsb_test import NumpyTestCase, RandomStorageFixture, skip_parallel
from neo import AnalogSignal, Block, Segment, SpikeTrain
from neo import io as neo_io
from quantities import ms, mV

from bsb import (
    Branch,
    Configuration,
    Morphology,
    MorphologySet,
    ResultsError,
    ResultsWarning,
    RotationSet,
    Scaffold,
    SimulationResult,
    read_results,
)
from bsb.simulation.results import (
    cell_annotations,
    iter_recordings,
    merge_rank_results,
    point_annotations,
    rank_part_path,
    read_provenance,
    read_simulation_config,
    synapse_annotations,
)
from bsb.storage.provenance import encode_annotation, get_provenance_version


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


class TestIterRecordings(unittest.TestCase):
    def test_a_cell_is_singled_out_by_model_and_id(self):
        # A cell id is only unique within its cell model.
        segment = Segment()
        for model in ("a", "b"):
            for cell_id in range(2):
                segment.spiketrains.append(
                    SpikeTrain(
                        [] * ms,
                        t_stop=10 * ms,
                        bsb_device_name="rec",
                        bsb_recording_kind="cell",
                        bsb_direction="record",
                        bsb_ps_name=model,
                        bsb_cell_model=model,
                        bsb_cell_id=cell_id,
                    )
                )

        self.assertEqual(2, len(list(iter_recordings(segment, cell_id=1))))
        (recording,) = iter_recordings(segment, cell_id=1, cell_model="b")
        self.assertEqual(
            ("rec", "cell", "record"),
            (recording.device, recording.kind, recording.direction),
        )
        self.assertEqual("b", recording.annotations["bsb_cell_model"])
        self.assertEqual(4, len(list(iter_recordings(segment, kind="cell"))))
        self.assertEqual([], list(iter_recordings(segment, kind="synapse")))
        self.assertEqual(2, len(list(iter_recordings(segment, cell_model="a"))))


@skip_parallel
class TestRecordedLocations(
    RandomStorageFixture, NumpyTestCase, unittest.TestCase, engine_name="hdf5"
):
    """Locations on a morphology are placed in the network as their cell is."""

    def setUp(self):
        super().setUp()
        cfg = Configuration.default(
            cell_types=dict(line=dict(spatial=dict(radius=1, count=2)))
        )
        self.network = Scaffold(cfg, self.storage)
        # Branch 0 runs 10 along x, branch 1 runs 8 along z in two steps.
        morphology = Morphology(
            [
                Branch([[0, 0, 0], [10, 0, 0]], [1, 1]),
                Branch([[0, 0, 0], [0, 0, 4], [0, 0, 8]], [1, 1, 1]),
            ]
        )
        stored = self.network.morphologies.save("line", morphology)
        self.network.place_cells(
            self.network.cell_types.line,
            [[100, 0, 0], [0, 50, 0]],
            morphologies=MorphologySet([stored], [0, 0]),
            # The first cell is turned a quarter around z, the second not at all.
            rotations=RotationSet([[0, 0, 90], [0, 0, 0]]),
        )
        tmpdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmpdir, ignore_errors=True)
        self.filename = pathlib.Path(tmpdir) / "locations.nio"

    def _write(self, *annotations):
        block = Block(name="sim")
        block.annotate(
            bsb_provenance=encode_annotation(
                {
                    "schema_version": get_provenance_version(),
                    "scaffold": {
                        "storage_id": self.network.storage_id,
                        "state_id": self.network.state_id,
                    },
                }
            )
        )
        segment = Segment()
        for annotation in annotations:
            segment.analogsignals.append(
                AnalogSignal(
                    [0.0, 0.0] * mV,
                    sampling_period=1 * ms,
                    name="v",
                    bsb_device_name="rec",
                    **annotation,
                )
            )
        block.segments.append(segment)
        with neo_io.NixIO(str(self.filename), mode="ow") as out:
            out.write_block(block)

    def test_positions_follow_the_morphology_rotation_and_position(self):
        model = types.SimpleNamespace(
            name="line_model", cell_type=types.SimpleNamespace(name="line")
        )
        self._write(
            point_annotations(model, 0, 0, 0, 0.5, "record"),
            synapse_annotations(
                model, 1, 1, 1, 0.75, "ExpSyn", "record", presynaptic=(model, 0)
            ),
        )

        results = read_results(self.network, self.filename)
        point, synapse = (recording.target for recording in results.recordings())

        # Halfway along branch 0 is 5 along x, turned onto y, at the first cell.
        self.assertClose([100, 5, 0], point.position)
        # Three quarters along branch 1 is 6 along z, at the unturned second cell.
        self.assertClose([0, 50, 6], synapse.position)
        # The morphology is the cell's, as it is in the network.
        placed = point.cell.morphology
        self.assertEqual(2, len(placed.branches))
        self.assertClose([[100, 0, 0], [100, 10, 0]], placed.branches[0].points)
        self.assertClose(
            [[0, 50, 0], [0, 50, 4], [0, 50, 8]],
            synapse.cell.morphology.branches[1].points,
        )
        self.assertClose([0, 0, 90], point.cell.rotation.as_euler("xyz", degrees=True))
        self.assertEqual(0, synapse.presynaptic.id)
        self.assertClose([100, 0, 0], synapse.presynaptic.position)


class _Simulation:
    """The little of a simulation a result reads."""

    name = "sim"
    duration = 10

    def __tree__(self):
        return {}


class TestRecordingsSayWhatTheyRecord(unittest.TestCase):
    """A result only writes recordings of a device that say what they recorded."""

    def setUp(self):
        self.result = SimulationResult(_Simulation())
        self.device = types.SimpleNamespace(name="rec", device="test_recorder")
        self.model = types.SimpleNamespace(
            name="model", cell_type=types.SimpleNamespace(name="cells")
        )

    def _train(self, **annotations):
        return SpikeTrain([1.0] * ms, t_stop=10 * ms, name="spikes", **annotations)

    def test_a_recorder_belongs_to_a_device(self):
        with self.assertRaises(TypeError):
            self.result.create_recorder(lambda segment: None)
        with self.assertRaises(ResultsError):
            self.result.create_recorder(lambda segment: None, None)

    def test_a_recording_that_says_nothing_is_not_written(self):
        def flush(segment):
            segment.spiketrains.append(self._train())
            segment.spiketrains.append(
                self._train(**cell_annotations(self.model, 3, "record"))
            )
            segment.spiketrains.append(
                self._train(**cell_annotations(self.model, 4, "sideways"))
            )

        self.result.create_recorder(flush, self.device)

        with self.assertWarns(ResultsWarning) as caught:
            self.result.flush()

        (kept,) = self.result.block.segments[0].spiketrains
        self.assertEqual(3, kept.annotations["bsb_cell_id"])
        self.assertEqual("rec", kept.annotations["bsb_device_name"])
        self.assertEqual("test_recorder", kept.annotations["bsb_device_kind"])
        self.assertIn("rec", str(caught.warning))


class TestProvenanceReading(unittest.TestCase):
    """Reading a results file back, including one written by another BSB."""

    def test_a_bundle_round_trips(self):
        bundle = {"schema_version": get_provenance_version(), "simulation_id": "abc"}
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
                {"schema_version": get_provenance_version() + 1, "simulation_id": "abc"}
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
