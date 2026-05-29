"""Tests for the simulation result provenance bundle + recorder convention helpers."""

import unittest

import numpy as np
from bsb.simulation.results import (
    Recording,
    SimulationResult,
    iter_recordings,
)


class _StubScaffold:
    def __init__(self):
        self.storage_id = "test-storage-uuid"
        self.state_id = 7

        class _Storage:
            root = "/tmp/stub"

        self.storage = _Storage()
        self._comm = _Comm()


class _Comm:
    def get_size(self):
        return 1


class _StubSimulation:
    name = "stub"
    seed = 42
    duration = 100.0
    resolution = 0.1

    def __init__(self):
        self.scaffold = _StubScaffold()

    def __tree__(self):
        return {"name": self.name}


class _StubCellModel:
    name = "pc"


class _StubDevice:
    name = "sr_pc"
    classmap_entry = "spike_recorder"


class TestSimulationResultProvenance(unittest.TestCase):
    def test_block_carries_bsb_provenance(self):
        result = SimulationResult(_StubSimulation())
        prov = result.block.annotations["bsb_provenance"]
        self.assertEqual(prov["schema_version"], 1)
        self.assertEqual(prov["simulation_name"], "stub")
        self.assertEqual(prov["scaffold"]["storage_id"], "test-storage-uuid")
        self.assertEqual(prov["scaffold"]["state_id"], 7)
        self.assertEqual(prov["mpi_size"], 1)
        self.assertIn("plugins", prov)
        self.assertIn("host", prov)

    def test_simulator_metadata_lands_on_block(self):
        result = SimulationResult(_StubSimulation())
        result.set_simulator("nest", version="3.7", modules=["a", "b"])
        prov = result.block.annotations["bsb_provenance"]
        self.assertEqual(prov["simulator"]["name"], "nest")
        self.assertEqual(prov["simulator"]["version"], "3.7")
        self.assertEqual(prov["simulator"]["extra"]["modules"], ["a", "b"])

    def test_mark_started_and_finished_stamps_timing(self):
        result = SimulationResult(_StubSimulation())
        result.mark_started()
        result.mark_finished(wall_seconds=1.25)
        prov = result.block.annotations["bsb_provenance"]
        self.assertIsNotNone(prov["started_at"])
        self.assertIsNotNone(prov["finished_at"])
        self.assertEqual(prov["wall_seconds"], 1.25)

    def test_flush_creates_segment_with_id(self):
        result = SimulationResult(_StubSimulation())
        # Run an empty flush to verify the segment metadata.
        result.flush()
        self.assertEqual(len(result.block.segments), 1)
        seg = result.block.segments[0]
        self.assertIn("segment_id", seg.annotations)
        self.assertEqual(seg.annotations["checkpoint_index"], 0)


class TestRecorderConventionHelpers(unittest.TestCase):
    def setUp(self):
        self.result = SimulationResult(_StubSimulation())
        # Pretend we're inside a flush so segment_id is populated.
        self.result.flush()
        # flush() resets segment_id back to None; re-set it for the test.
        self.result._segment_id = self.result.block.segments[0].annotations[
            "segment_id"
        ]

    def test_spike_train_has_standard_annotations(self):
        st = self.result.spike_train(
            times=[1.0, 2.0, 3.0],
            ps_name="pc",
            cell_id=17,
            cell_model=_StubCellModel(),
            device=_StubDevice(),
            t_stop=100.0,
        )
        # Baseline layer.
        self.assertEqual(st.annotations["bsb_device_name"], "sr_pc")
        self.assertEqual(st.annotations["bsb_device_kind"], "spike_recorder")
        self.assertEqual(st.annotations["bsb_target_kind"], "cell")
        self.assertEqual(
            st.annotations["bsb_simulation_id"], self.result.simulation_id
        )
        self.assertIsNotNone(st.annotations["bsb_segment_id"])
        # Cell-target layer.
        self.assertEqual(st.annotations["bsb_ps_name"], "pc")
        self.assertEqual(st.annotations["bsb_cell_id"], 17)
        self.assertEqual(st.annotations["bsb_cell_model"], "pc")

    def test_analog_signal_target_kind(self):
        import quantities as pq

        sig = self.result.analog_signal(
            data=np.array([1.0, 2.0, 3.0]),
            units="mV",
            sampling_period=1.0 * pq.ms,
            name="V_m",
            target_kind="compartment",
            ps_name="pc",
            cell_id=3,
            cell_model=_StubCellModel(),
            device=_StubDevice(),
            branch=2,
            point=5,
            arc=0.5,
        )
        self.assertEqual(sig.name, "V_m")
        self.assertEqual(sig.annotations["bsb_target_kind"], "compartment")
        self.assertEqual(sig.annotations["bsb_ps_name"], "pc")
        self.assertEqual(sig.annotations["bsb_cell_id"], 3)
        # per-kind fields are flat bsb_* siblings, not nested under bsb_location
        self.assertEqual(sig.annotations["bsb_branch"], 2)
        self.assertEqual(sig.annotations["bsb_point"], 5)
        self.assertEqual(sig.annotations["bsb_arc"], 0.5)
        self.assertNotIn("bsb_location", sig.annotations)


class TestIterRecordings(unittest.TestCase):
    def test_skips_non_bsb_neo_objects(self):
        from neo import Block, Segment, SpikeTrain

        result = SimulationResult(_StubSimulation())
        result.flush()
        seg = result.block.segments[0]
        # Compliant: standard annotations present.
        result._segment_id = seg.annotations["segment_id"]
        seg.spiketrains.append(
            result.spike_train(
                times=[1.0],
                ps_name="pc",
                cell_id=0,
                cell_model=_StubCellModel(),
                device=_StubDevice(),
                t_stop=10.0,
            )
        )
        # Non-compliant: bare SpikeTrain with no bsb_ps_name.
        seg.spiketrains.append(SpikeTrain([2.0], units="ms", t_stop=10.0))
        records = list(iter_recordings(result.block))
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0].ps_name, "pc")
        self.assertEqual(records[0].cell_id, 0)
        self.assertIsInstance(records[0], Recording)
        _ = Block, Segment  # silence unused-import linters


if __name__ == "__main__":
    unittest.main()
