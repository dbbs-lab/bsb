import os
import unittest
from os.path import abspath, dirname, join
from sys import path

from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestGettingStartedExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def _test_scaffold_results(self):
        self.assertEqual(
            len(self.scaffold.cell_types["base_type"].get_placement_set()), 1560
        )
        self.assertEqual(
            len(self.scaffold.cell_types["top_type"].get_placement_set()), 40
        )
        self.assertEqual(len(self.scaffold.get_connectivity_set("A_to_B")), 40 * 1560)

    def test_json_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "getting_started.json")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "getting_started.yaml")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_python_example(self):
        import scripts.getting_started  # noqa: F401

        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        # check if load_data runs without any problems
        import scripts.load_data  # noqa: F401

        os.remove("network.hdf5")
