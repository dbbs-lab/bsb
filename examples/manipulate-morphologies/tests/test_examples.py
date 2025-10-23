import os
import unittest
from os.path import abspath, dirname
from sys import path

from bsb import from_storage
from bsb_test import RandomStorageFixture

ROOT_FOLDER = abspath(dirname(dirname(__file__)))
path.insert(1, ROOT_FOLDER)


class TestManipulateMorphoExamples(
    RandomStorageFixture,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        os.chdir(ROOT_FOLDER)

    def test_python_example(self):
        import scripts.labels  # noqa: F401

        self.scaffold = from_storage("morphologies.hdf5")
        os.remove("morphologies.hdf5")