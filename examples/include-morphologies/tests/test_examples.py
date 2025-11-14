import os
import unittest
from os.path import abspath, dirname, isfile, join
from sys import path

from bsb import Scaffold, from_storage, parse_configuration_file
from bsb_test import RandomStorageFixture

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestIncludeMorphoExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        os.chdir(ROOT_FOLDER)

    def _test_scaffold_results(self):
        self.assertEqual(
            len(self.scaffold.cell_types["base_type"].get_placement_set()), 1560
        )
        self.assertEqual(
            len(self.scaffold.cell_types["top_type"].get_placement_set()), 40
        )
        self.assertGreater(len(self.scaffold.get_connectivity_set("A_to_B")), 1000)

    def test_json_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "include_morphos.json")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_yaml_example(self):
        self.cfg = parse_configuration_file(
            join(ROOT_FOLDER, "configs", "include_morphos.yaml")
        )
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        self._test_scaffold_results()

    def test_python_example(self):
        import scripts.include_morphos  # noqa: F401

        self.scaffold = from_storage("network.hdf5")
        self._test_scaffold_results()
        # check if plotting_with_branch_colors runs without any problems
        import scripts.plotting_with_branch_colors  # noqa: F401

        self.assertTrue(isfile("cell_morphology.png"))
        os.remove("network.hdf5")
        os.remove("cell_morphology.png")
