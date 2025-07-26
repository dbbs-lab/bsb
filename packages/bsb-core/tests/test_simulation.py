import unittest

import numpy as np
from bsb_test import FixedPosConfigFixture, NumpyTestCase, RandomStorageFixture

from bsb import MPI, Scaffold, get_simulation_adapter


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
        sim = self.network.simulations.test
        sim.devices["id_recorder"] = dict(
            device="spike_recorder",
            targetting={
                "strategy": "sphere",
                "origin": [20, 100, 100],
                "radius": 75,
            },
        )
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        results = adapter.run(sim)
        result = adapter.collect(results)[0]
        # check ids in sphere by positions, our sphere only include h_cells with x <= 40
        positions = [
            (simdata.placement[model].load_positions(), pop)
            for model, pop in simdata.populations.items()
        ]
        expected_ids = []
        for pos, id in zip(positions[0][0], positions[0][1], strict=False):
            if pos[0] <= 40:
                expected_ids.append(id)
        expected_ids = np.array(expected_ids)

        spiketrains = result.block.segments[0].spiketrains
        sorted_ids = np.sort(spiketrains[0].annotations["gids"])
        only_h_cells = sorted_ids[sorted_ids < 20]
        self.assertAll(only_h_cells == expected_ids)
        self.assertEqual(len(only_h_cells), 12)
