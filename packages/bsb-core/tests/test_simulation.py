import unittest

import numpy as np
from bsb_arbor import SpikeRecorder
from bsb_test import FixedPosConfigFixture, NumpyTestCase, RandomStorageFixture

from bsb import MPI, AdapterController, Scaffold, compose_nodes, config


class TestSimulate(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg.connectivity.add(
            "all_to_all",
            dict(
                strategy="bsb.connectivity.AllToAll",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["test_cell"]),
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile(clear=True)

    def test_simulate(self):
        self.network.simulations.add(
            "test",
            simulator="arbor",
            duration=100,
            resolution=1.0,
            cell_models=dict(),
            connection_models=dict(),
            devices=dict(),
        )
        self.network.run_simulation("test")


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestTargetting(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg.network.chunk_size = 50
        self.cfg.cell_types.add("h_cell", spatial=dict(radius=2, count=20))
        x_ranges = np.repeat(np.arange(0, 100, 20), 4)
        y_ranges = np.full((10, 2), [50, 150]).flatten()
        z_ranges = np.full((5, 4), [50, 50, 150, 150]).flatten()

        positions = []
        for x, y, z in zip(x_ranges, y_ranges, z_ranges, strict=False):
            positions.append([x, y, z])

        self.cfg.placement.add(
            "place_h_cell",
            strategy="bsb.placement.strategy.FixedPositions",
            partitions=[],
            cell_types=["h_cell"],
            positions=positions,
        )

        self.cfg.connectivity.add(
            "test_to_h_cell",
            dict(
                strategy="bsb.connectivity.FixedOutdegree",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["h_cell"]),
                outdegree=1,
            ),
        )
        self.cfg.simulations.add(
            "test",
            simulator="arbor",
            duration=100,
            resolution=0.5,
            cell_models={
                "test_cell": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
                "h_cell": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
            },
            connection_models={
                "test_to_h_cell": {"weight": 20.68015524367846, "delay": 1.5}
            },
            devices=dict(
                pg={
                    "device": "poisson_generator",
                    "rate": 1600,
                    "targetting": {"strategy": "all"},
                    "weight": 2000,
                    "delay": 1.5,
                }
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile()

    def test_cell_model(self):
        self.network.simulations.test.devices["new_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "cell_model",
                "cell_models": ["test_cell"],
            },
        )
        # Add two devices to test FractionFilter
        self.network.simulations.test.devices["fraction_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "cell_model",
                "cell_models": ["h_cell"],
                "fraction": 0.5,
            },
        )
        self.network.simulations.test.devices["count_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "cell_model",
                "cell_models": ["h_cell"],
                "count": 7,
            },
        )
        result = self.network.run_simulation("test")
        spiketrains = result.block.segments[0].spiketrains
        expected = {
            "count_recorder": {
                "size": 7,
                "min": 0,
                "max": 20,
            },
            "fraction_recorder": {
                "size": 10,
                "min": 0,
                "max": 20,
            },
            "new_recorder": {
                "size": 100,
                "min": 20,
                "max": 120,
            },
        }
        for spiketrain in spiketrains:
            recorder = spiketrain.annotations["device"]
            self.assertEqual(
                spiketrain.annotations["pop_size"], expected[recorder]["size"]
            )
            self.assertAll(
                np.array(spiketrain.annotations["gids"]) < expected[recorder]["max"]
            )
            self.assertAll(
                np.array(spiketrain.annotations["gids"]) >= expected[recorder]["min"]
            )

    def test_by_id(self):
        sim = self.network.simulations.test
        sim.devices["id_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "by_id",
                "ids": {"h_cell": [0, 10, 7, 5]},
            },
        )
        result = self.network.run_simulation("test")
        spiketrains = result.block.segments[0].spiketrains
        self.assertEqual(sorted(spiketrains[0].annotations["gids"]), [0, 5, 7, 10])

    def test_sphere(self):
        """Testing SphericalTargetting and SphericalTargettingCellTypes together"""
        sim = self.network.simulations.test
        sim.devices["sphere_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "sphere",
                "origin": [20, 100, 100],
                "radius": 75,
            },
        )
        sim.devices["sphere_ct_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "sphere_cell_types",
                "cell_types": ["h_cell"],
                "origin": [20, 100, 100],
                "radius": 75,
            },
        )
        result = self.network.run_simulation("test")
        # check ids in sphere by positions, our sphere only include h_cells with x <= 40
        ps = self.network.get_placement_set("h_cell")
        positions = ps.load_positions()
        expected_ids = np.where(positions[:, 0] <= 40)

        print(f"result: {result} - len: {len(result.block.segments)}")
        spiketrains = result.block.segments[0].spiketrains
        for spiketrain in spiketrains:
            sorted_ids = np.sort(spiketrain.annotations["gids"])
            only_h_cells = sorted_ids[sorted_ids < 20]
            self.assertAll(only_h_cells == expected_ids)
            self.assertEqual(len(only_h_cells), 12)

    def test_cylinder(self):
        sim = self.network.simulations.test
        sim.devices["cyl_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "cylinder",
                "origin": [40, 50],
                "axis": "y",
                "radius": 30,
            },
        )
        result = self.network.run_simulation("test")
        # check ids in cylinder by positions, our cylinder only
        # include h_cells with z = 50 and 10 < x < 70
        ps = self.network.get_placement_set("h_cell")
        positions = ps.load_positions()

        filtered_by_cylinder = ((positions[:, 0] <= 60) & (positions[:, 0] >= 20)) & (
            positions[:, 2] == 50
        )
        expected_ids = np.where(filtered_by_cylinder)

        spiketrains = result.block.segments[0].spiketrains
        sorted_ids = np.sort(spiketrains[0].annotations["gids"])
        only_h_cells = sorted_ids[sorted_ids < 20]
        self.assertAll(only_h_cells == expected_ids)
        self.assertEqual(len(only_h_cells), 6)

    def test_bylabel(self):
        ps = self.network.get_placement_set("h_cell")
        positions = ps.load_positions()
        # should return 4 ids
        sub_pop_h_cell = np.where(positions[:, 0] == 80)[0]
        ps.label(labels=["only_x_80"], cells=sub_pop_h_cell)

        sim = self.network.simulations.test
        sim.devices["new_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "by_label",
                "cell_models": ["h_cell"],
                "labels": ["only_x_80"],
            },
        )
        result = self.network.run_simulation("test")
        spiketrains = result.block.segments[0].spiketrains

        sorted_ids = np.sort(spiketrains[0].annotations["gids"])
        self.assertAll(sorted_ids == sub_pop_h_cell)
        self.assertEqual(len(sorted_ids), 4)


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestAdapterController(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg.network.chunk_size = 50
        self.cfg.cell_types.add("h_cell", spatial=dict(radius=2, count=20))
        x_ranges = np.repeat(np.arange(0, 100, 20), 4)
        y_ranges = np.full((10, 2), [50, 150]).flatten()
        z_ranges = np.full((5, 4), [50, 50, 150, 150]).flatten()

        positions = []
        for x, y, z in zip(x_ranges, y_ranges, z_ranges, strict=False):
            positions.append([x, y, z])

        self.cfg.placement.add(
            "place_h_cell",
            strategy="bsb.placement.strategy.FixedPositions",
            partitions=[],
            cell_types=["h_cell"],
            positions=positions,
        )

        self.cfg.connectivity.add(
            "test_to_h_cell",
            dict(
                strategy="bsb.connectivity.FixedOutdegree",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["h_cell"]),
                outdegree=1,
            ),
        )
        self.cfg.simulations.add(
            "test",
            simulator="arbor",
            duration=100,
            resolution=0.5,
            cell_models={
                "test_cell": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
                "h_cell": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
            },
            connection_models={
                "test_to_h_cell": {"weight": 20.68015524367846, "delay": 1.5}
            },
            devices=dict(
                pg={
                    "device": "poisson_generator",
                    "rate": 1600,
                    "targetting": {"strategy": "all"},
                    "weight": 2000,
                    "delay": 1.5,
                }
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile()

    def test_record_checkpoint(self):
        """Create a test with an AdapterController that flushes every 10 steps,
        so with a simulation of 100 of duration it will create 10 segments plus
        a last one that is empty"""

        class FixedStepController(AdapterController):
            def __init__(self, **kwargs):
                self._status = 0
                self._step = 10
                self.need_flush = True

            def get_next_checkpoint(self):
                return self._status + self._step

            def progress(self, kwargs=None):
                self._status += self._step
                return self._status

        @config.node
        class SpikeController(
            compose_nodes(SpikeRecorder, FixedStepController),
            classmap_entry="spike_controller",
        ):
            def __init__(self, **kwargs):
                FixedStepController.__init__(self)
                super().__init__()

        self.network.simulations.test.devices["new_recorder"] = dict(
            device="spike_controller",
            targetting={
                "strategy": "cell_model",
                "cell_models": ["test_cell"],
            },
        )
        result = self.network.run_simulation("test")
        segments = result.block.segments

        self.assertEqual(
            len(segments),
            11,
            "The simulation should have been split in 10 populated segments + 1 empty",
        )
        self.assertEqual(
            list(segments[-1].spiketrains[0].magnitude),
            [],
            "The eleventh segment should be empty",
        )
        # Spiketrains in the nth segment should have values between n*10 and (n+1)*10
        self.assertAll(
            segments[6].spiketrains[0].magnitude >= 60,
            "Times in the 6th segment do not start from 60.",
        )
        self.assertAll(
            segments[6].spiketrains[0].magnitude < 70,
            "Spike times in segment 6 fall outside the expected range (60–70).",
        )

    def test_async_checkpoint(self):
        """Create a test with an AdapterController that flushes every 15 steps,
        the simulation of duration 100 will be flushed 7 times but the end will
        not align to a checkpoint"""

        class FixedStepController(AdapterController):
            def __init__(self, **kwargs):
                self._status = 0
                self._step = 15
                self.need_flush = True

            def get_next_checkpoint(self):
                return self._status + self._step

            def progress(self, kwargs=None):
                self._status += self._step
                return self._status

        @config.node
        class SpikeController(
            compose_nodes(SpikeRecorder, FixedStepController),
            classmap_entry="spike_controller",
        ):
            def __init__(self, **kwargs):
                FixedStepController.__init__(self)
                super().__init__()

        self.network.simulations.test.devices["new_recorder"] = dict(
            device="spike_controller",
            targetting={
                "strategy": "cell_model",
                "cell_models": ["test_cell"],
            },
        )
        result = self.network.run_simulation("test")
        segments = result.block.segments

        self.assertEqual(
            len(segments),
            7,
            "The simulation should have been split in 7 populated segments",
        )

        # Check that results in the last part, after last checkpoint, is correctly flushed
        self.assertAll(
            segments[-1].spiketrains[0].magnitude >= 90,
            "Times in the last segment do not start from 90.",
        )
        self.assertAll(
            segments[-1].spiketrains[0].magnitude < 100,
            "Spike times in last segment fall outside the expected range (90-100).",
        )
