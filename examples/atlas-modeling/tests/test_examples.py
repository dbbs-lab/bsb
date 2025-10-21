import os
import unittest
from os.path import abspath, dirname, join
from sys import path

from bsb import Scaffold, parse_configuration_file
from bsb_test import RandomStorageFixture, skip_test_allen_api

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


@unittest.skipIf(
    skip_test_allen_api(),
    "Allen API is down",
)
class TestAtlasExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        os.chdir(ROOT_FOLDER)
        super().setUp()

    def test_json_example(self):
        self.cfg = parse_configuration_file(join(ROOT_FOLDER, "configs", "allen_structure.json"))
        self.scaffold = Scaffold(self.cfg, self.storage)
        self.scaffold.compile()
        nb_voxels_dec_ccfv3 = 213303
        self.assertEqual(
            len(self.scaffold.partitions["declive"].to_voxels()), nb_voxels_dec_ccfv3
        )
        self.assertLess(
            abs(
                len(self.scaffold.cell_types["my_cell"].get_placement_set())
                - nb_voxels_dec_ccfv3 * 0.003 * 25**3
            ),
            100,
        )
        self.assertEqual(
            len(self.scaffold.cell_types["my_other_cell"].get_placement_set()),
            nb_voxels_dec_ccfv3,
        )

    def test_python_example(self):
        # should run without errors
        import scripts.allen_structure  # noqa: F401
