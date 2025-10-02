import os
import unittest
from os.path import abspath, dirname, join
from sys import path

from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture

CONFIG_FOLDER = abspath(join(dirname(dirname(__file__)), "cell_labeling"))
path.insert(1, CONFIG_FOLDER)


class TestCellLabelingExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        os.chdir(CONFIG_FOLDER)

    def _test_scaffold_results(self):
        self.assertEqual(
            len(self.scaffold.cell_types["cell_A"].get_placement_set()), 1560
        )

    def test_json_example(self):
        self.cfg = parse_configuration_file(join(CONFIG_FOLDER, "cell_labeling.json"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(join(CONFIG_FOLDER, "cell_labeling.yaml"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_python_example(self):
        import cell_labeling  # noqa: F401

        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        # check if load_data runs without any problems
        import test_labels  # noqa: F401

        os.remove("network.hdf5")
