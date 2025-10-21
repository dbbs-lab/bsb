import os
import unittest
from os.path import abspath, dirname, join
from sys import path

from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestCellLabelingExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        os.chdir(ROOT_FOLDER)
        super().setUp()

    def _test_scaffold_results(self):
        self.assertEqual(
            len(self.scaffold.cell_types["cell_A"].get_placement_set()), 1560
        )

    def test_json_example(self):
        self.cfg = parse_configuration_file(join(ROOT_FOLDER, "configs", "cell_labeling.json"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(join(ROOT_FOLDER, "configs", "cell_labeling.yaml"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_python_example(self):
        import scripts.cell_labeling  # noqa: F401

        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        # check if load_data runs without any problems
        import scripts.test_labels  # noqa: F401

        os.remove("network.hdf5")
