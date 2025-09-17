import os
from os.path import dirname, abspath, join
import unittest

from bsb import parse_configuration_file, Scaffold, from_storage
from bsb_test import RandomStorageFixture

CONFIG_FOLDER = abspath(join(dirname(dirname(__file__)), "getting_started"))


class TestExamples(
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
        self.cfg = parse_configuration_file(join(CONFIG_FOLDER, "getting_started.json"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(join(CONFIG_FOLDER, "getting_started.yaml"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_python_example(self):
        import getting_started.geting_started
        # check if load_data runs without any problems
        import getting_started.load_data
        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        os.remove("network.hdf5")
