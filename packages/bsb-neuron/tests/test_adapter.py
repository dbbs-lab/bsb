import unittest

import numpy as np
from bsb import get_simulation_adapter
from bsb_test import (
    ConfigFixture,
    MorphologiesFixture,
    NetworkFixture,
    NumpyTestCase,
    RandomStorageFixture,
)
from patch import p

from bsb_neuron.cell import ArborizedModel
from bsb_neuron.connection import TransceiverModel


class TestNeuronPopulation(
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
        p.parallel.gid_clear()
        for ct in self.network.cell_types.values():
            ct.spatial.morphologies = ["2comp"]
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {}},
        }
        self.network.simulations.add(
            "test",
            simulator="neuron",
            duration=25,
            resolution=0.1,
            temperature=32,
            cell_models=dict(
                A=ArborizedModel(model=hh_soma),
                B=ArborizedModel(model=hh_soma),
                C=ArborizedModel(model=hh_soma),
            ),
            connection_models=dict(
                A_to_B=TransceiverModel(synapses=[dict(synapse="ExpSyn", delay=0.5)]),
                B_to_C=TransceiverModel(synapses=[dict(synapse="ExpSyn", delay=0.5)]),
            ),
            devices={},
        )

    def test_getitem(self):
        """
        Test if getitem method works as expected for all int and bool data types.
        """
        self.network.compile()
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)

        pop = simdata.populations[sim.cell_models["A"]]
        ids = np.array([cell.id for cell in simdata.populations[sim.cell_models["A"]]])

        all_tests = np.array([])
        # test int list and np.int64 array
        list_test = [0, 1, 3]
        np.append(all_tests, [ele.id for ele in pop[list_test]] == ids[list_test])
        int64_test = np.array(list_test, dtype=np.int64)
        np.append(all_tests, [ele.id for ele in pop[int64_test]] == ids[int64_test])
        int8_test = np.array(list_test, dtype=np.int8)
        np.append(all_tests, [ele.id for ele in pop[int8_test]] == ids[int8_test])
        uint_test = np.array(list_test, dtype=np.uint)
        np.append(all_tests, [ele.id for ele in pop[uint_test]] == ids[uint_test])
        # test bool
        bool_test = [True for ele in pop]
        np.append(all_tests, [ele.id for ele in pop[bool_test]] == ids[bool_test])
        npbool_test = np.array(bool_test, dtype=np.bool_)
        np.append(all_tests, [ele.id for ele in pop[npbool_test]] == ids[npbool_test])

        self.assertAll(all_tests)

        # test float
        float_test = np.array(list_test, dtype=np.float32)
        with self.assertRaises(TypeError):
            pop[float_test]
