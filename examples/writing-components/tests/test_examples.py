import os
from os.path import dirname, abspath, join
from sys import path
import unittest

from bsb import parse_configuration_file, Scaffold, from_storage
from bsb_test import RandomStorageFixture

CONFIG_FOLDER = abspath(join(dirname(dirname(__file__)), "writing_components"))


class TestExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        path.insert(1, CONFIG_FOLDER)

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
            join(CONFIG_FOLDER, "writing_components.json")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(
            join(CONFIG_FOLDER, "writing_components.yaml")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()

    def test_python_example(self):
        self.scaffold = from_storage("network.hdf5")
        os.remove("network.hdf5")
