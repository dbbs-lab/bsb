import os
import shutil
import unittest
from os.path import abspath, dirname, isdir, isfile, join
from sys import path

import numpy as np
from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture
from neo import io

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestNestExamples(
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
        self.assertEqual(
            len(self.scaffold.cell_types["base_type"].get_placement_set()), 1560
        )
        self.assertEqual(
            len(self.scaffold.cell_types["top_type"].get_placement_set()), 40
        )
        self.assertEqual(len(self.scaffold.get_connectivity_set("A_to_B")), 40 * 1560)

    def _test_simulation_results(self, spiketrains):
        neuron_ids = []
        self.assertEqual(len(spiketrains), 3)
        for signal in spiketrains:
            neuron_ids = np.concatenate(
                [neuron_ids, np.unique(signal.array_annotations["senders"])]
            )
            self.assertEqual(signal.t_start, 0)
            self.assertEqual(signal.t_stop, 5000)

        # test the number of cell recorded
        self.assertLess(neuron_ids.size, 1600 + 1)
        self.assertEqual(np.max(neuron_ids), 1600 + 1)

    def test_json_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "guide_nest.json")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()
        results = self.scaffold.run_simulation("basal_activity")
        self._test_simulation_results(results.block.segments[0].spiketrains)

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "guide_nest.yaml")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()
        results = self.scaffold.run_simulation("basal_activity")
        self._test_simulation_results(results.block.segments[0].spiketrains)

    def test_python_example(self):
        import scripts.guide_nest  # noqa: F401

        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        self.assertTrue(isfile("simulation-results/basal_activity.nio"))
        results = io.NixIO("simulation-results/basal_activity.nio", mode="ro")
        self._test_simulation_results(
            results.read_all_blocks()[0].segments[0].spiketrains
        )
        # check if analyze analog results runs without any problems
        import scripts.analyze_spike_results  # noqa: F401

        files = os.listdir("simulation-results")  # 1 png and 1 nio file
        self.assertTrue("raster_plot.png" in files)
        self.assertEqual(len(files), 2)

        import scripts.repeated_simulations  # noqa: F401

        files = os.listdir("simulation-results")
        self.assertEqual(len(files), 12)

        os.remove("network.hdf5")
