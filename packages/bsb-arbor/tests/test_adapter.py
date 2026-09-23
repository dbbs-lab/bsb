import unittest

import numpy as np
from bsb import MPI, get_simulation_adapter
from bsb_test import (
    ConfigFixture,
    MorphologiesFixture,
    NetworkFixture,
    NumpyTestCase,
    RandomStorageFixture,
)


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestArborPopulation(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    NumpyTestCase,
    unittest.TestCase,
    config="chunked",
    morpho_filters=["2comp"],
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()

        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["2comp"]
        self.network.configuration.network.chunk_size = 200
        self.network.configuration.simulations.add(
            "test",
            simulator="arbor",
            duration=25,
            resolution=0.1,
            cell_models=dict(
                A={"model_strategy": "lif"},
                B={"model_strategy": "lif"},
                C={"model_strategy": "lif"},
            ),
            connection_models={},
            devices={},
        )

    def test_getitem(self):
        """
        Test if getitem method works as expected for all int and bool data types, on
        every population, including those whose gids start at an offset.
        """
        self.network.compile(clear=True)
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)

        list_test = [0, 1, 3, 11]
        for name in ("A", "B", "C"):
            with self.subTest(model=name):
                pop = simdata.populations[sim.cell_models[name]]
                gids = np.array(list(pop))
                for index in (
                    list_test,
                    np.array(list_test, dtype=np.int64),
                    np.array(list_test, dtype=np.int8),
                    np.array(list_test, dtype=np.uint),
                ):
                    self.assertEqual(gids[list_test].tolist(), list(pop[index]))
                mask = np.arange(len(pop)) % 2 == 0
                self.assertEqual(gids[mask].tolist(), list(pop[mask]))
                self.assertEqual(gids[mask].tolist(), list(pop[mask.tolist()]))
                self.assertEqual([], list(pop[np.zeros(len(pop), dtype=bool)]))
                for item in (0, 5, 11):
                    self.assertEqual([gids[item]], list(pop[item]))
                    self.assertEqual([gids[item]], list(pop[np.int64(item)]))

                # test float
                float_test = np.array(list_test, dtype=np.float32)
                with self.assertRaises(ValueError):
                    pop[float_test]
