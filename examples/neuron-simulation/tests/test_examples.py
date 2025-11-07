import os
import re
import shutil
import unittest
from os.path import abspath, dirname, isdir, isfile, join
from sys import path

from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture
from neo import io

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestNeuronExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def _cleanup(self):
        if isdir("simulation-results"):
            shutil.rmtree("simulation-results")

    def setUp(self):
        os.chdir(ROOT_FOLDER)
        super().setUp()
        self._cleanup()

    def tearDown(self):
        super().tearDown()
        self._cleanup()

    def _test_scaffold_results(self):
        ps = self.scaffold.cell_types["stellate_cell"].get_placement_set()

        self.assertEqual(len(ps), 30)
        morphologies = ps.load_morphologies()
        self.assertEqual(len(morphologies), 30)
        self.assertEqual(morphologies.names, ["StellateCell"])
        self.assertGreater(
            len(self.scaffold.get_connectivity_set("stellate_to_stellate")), 50
        )

    def _test_simulation_results(self, analogsignals):
        count_neurons = 0
        count_synapses = 0
        for signal in analogsignals:
            if signal.name == "vrecorder":
                count_neurons += 1
            if signal.name == "synapses_rec":
                count_synapses += 1
            self.assertEqual(signal.t_start, 0)
            # simulation should last 100 ms + 1 dt
            self.assertEqual(signal.t_stop, 0.100025)  # in s
            self.assertEqual(len(signal.magnitude), 100 / 0.025 + 1)

        # we should get some results for each recording type
        self.assertGreater(count_neurons, 5)
        self.assertGreater(count_synapses, 10)

    def test_json_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "guide_neuron.json")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()
        results = self.scaffold.run_simulation("neuronsim")
        self._test_simulation_results(results.analogsignals)

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "guide_neuron.yaml")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()
        results = self.scaffold.run_simulation("neuronsim")
        self._test_simulation_results(results.analogsignals)

    def test_python_example(self):
        import scripts.guide_neuron  # noqa: F401

        self.scaffold = from_storage("my_network.hdf5")
        self._test_scaffold_results()
        self.assertTrue(isfile("simulation-results/neuronsimulation.nio"))
        results = io.NixIO("simulation-results/neuronsimulation.nio", mode="ro")
        self._test_simulation_results(
            results.read_all_blocks()[0].segments[0].analogsignals
        )
        # check if analyze analog results runs without any problems
        import scripts.analyze_analog_results  # noqa: F401

        files = os.listdir("simulation-results")  # two pngs 1 nio file
        self.assertEqual(len(files), 3)
        self.assertTrue(any([re.search("^vrecorder_[0-9]+\.png$", f) for f in files]))
        self.assertTrue(
            any([re.search("^synapses_rec_[0-9]+_.+\.png$", f) for f in files])
        )

        os.remove("my_network.hdf5")
