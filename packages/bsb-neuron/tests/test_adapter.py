import importlib
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


def neuron_installed():
    return importlib.util.find_spec("neuron")


@unittest.skipIf(not neuron_installed(), "NEURON is not installed")
class TestTargetting(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
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

    def test_byid(self):
        """
        Test if by_id targetting strategy correctly selects neurons in NeuronPopulation
        """
        target_ids = {"A": [1, 3], "B": [5, 7], "C": [6]}
        self.network.simulations.test.devices["new_current"] = dict(
            device="current_clamp",
            targetting={
                "strategy": "by_id",
                "ids": target_ids,
            },
            locations={"strategy": "soma"},
            before=5,
            amplitude=50,
            duration=1,
        )

        self.network.compile()
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)
        results = adapter.run(sim)
        result = adapter.collect(results)[0]

        ids = []
        for cm in sim.cell_models:
            pop = [cell.id for cell in simdata.populations[sim.cell_models[cm]]]
            pop_chunk = [ele for ele in pop if ele in target_ids[cm]]
            ids.append(pop_chunk)

        control_results = {"A": ids[0], "B": ids[1], "C": ids[2]}
        res_dict = {"A": [], "B": [], "C": []}
        for signal in result.analogsignals:
            res_dict[signal.annotations["cell_type"]].append(
                signal.annotations["cell_id"]
            )
        self.assertEqual(res_dict, control_results)

    def test_sphere(self):
        """
        Test if sphere targetting strategy correctly selects neurons in NeuronPopulation,
        neurons are placed in a grid separated by 10 um
        """
        self.network.simulations.test.devices["sphere_current"] = dict(
            device="current_clamp",
            targetting={"strategy": "sphere", "origin": [20, 10, 10], "radius": 15},
            locations={"strategy": "soma"},
            before=5,
            amplitude=50,
            duration=1,
        )

        self.network.compile()
        sim = self.network.simulations.test
        adapter = get_simulation_adapter(sim.simulator)
        simdata = adapter.prepare(sim)

        results = adapter.run(sim)
        result = adapter.collect(results)[0]

        ids = []
        for cm in sim.cell_models:
            pop = [cell.id for cell in simdata.populations[sim.cell_models[cm]]]
            pop_chunk = [ele for ele in pop if ele in [0, 1, 2]]
            ids.append(pop_chunk)

        control_results = {"A": ids[0], "B": ids[1], "C": ids[2]}
        res_dict = {"A": [], "B": [], "C": []}
        for signal in result.analogsignals:
            res_dict[signal.annotations["cell_type"]].append(
                signal.annotations["cell_id"]
            )
        self.assertEqual(res_dict, control_results)


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
