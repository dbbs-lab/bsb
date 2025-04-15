import json
import os
import unittest

import h5py
import numpy as np
from bsb import MPI, Storage


class TestHandcrafted(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if MPI.get_rank() == 0:
            with h5py.File("test.h5", "w") as f:
                g = f.create_group("morphologies")
                g = g.create_group("M")
                ds = g.create_dataset("data", data=np.empty((0, 5)))
                ds.attrs["labels"] = json.dumps({0: []})
                ds.attrs["properties"] = []
                g.create_dataset("graph", data=[])
                f.create_dataset("morphology_meta", data=json.dumps({"M": {}}))
            with h5py.File("test2.h5", "w") as f:
                g = f.create_group("morphologies")
                g = g.create_group("M")
                ds = g.create_dataset("data", data=np.empty((0, 5)))
                ds.attrs["labels"] = json.dumps({0: []})
                ds.attrs["properties"] = []
                g.create_dataset("graph", data=[[0, -1], [0, -1], [0, -1]])
                f.create_dataset("morphology_meta", data=json.dumps({"M": {}}))
            with h5py.File("test3.h5", "w") as f:
                g = f.create_group("morphologies")
                g = g.create_group("M")
                ds = g.create_dataset("data", data=np.ones((1, 5)))
                ds.attrs["labels"] = json.dumps({1: []})
                ds.attrs["properties"] = []
                g.create_dataset("graph", data=[[0, -1]])
                f.create_dataset("morphology_meta", data=json.dumps({"M": {}}))
            with h5py.File("test4.h5", "w") as f:
                g = f.create_group("morphologies")
                g = g.create_group("M")
                data = np.ones((5, 5))
                data[:, 0] = np.arange(5) * 2
                data[:, 1] = np.arange(5) * 2
                data[:, 2] = np.arange(5) * 2
                data[:, 3] = np.arange(5) * 2
                ds = g.create_dataset("data", data=data)
                ds.attrs["labels"] = json.dumps({1: []})
                ds.attrs["properties"] = []
                g.create_dataset("graph", data=[[i + 1, -1] for i in range(5)])
                f.create_dataset("morphology_meta", data=json.dumps({"M": {}}))
            with h5py.File("test5.h5", "w") as f:
                g = f.create_group("morphologies")
                g = g.create_group("M")
                data = np.ones((5, 5))
                data[:, 0] = np.arange(5) * 2
                data[:, 1] = np.arange(5) * 2
                data[:, 2] = np.arange(5) * 2
                data[:, 3] = np.arange(5) * 2
                ds = g.create_dataset("data", data=data)
                ds.attrs["labels"] = json.dumps({1: []})
                ds.attrs["properties"] = []
                g.create_dataset(
                    "graph", data=[[i + 1, -1] for i in range(4)] + [[5, 0]]
                )
                f.create_dataset("morphology_meta", data=json.dumps({"M": {}}))
        MPI.barrier()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if MPI.get_rank() == 0:
            os.remove("test.h5")
            os.remove("test2.h5")
            os.remove("test3.h5")
            os.remove("test4.h5")
            os.remove("test5.h5")
        MPI.barrier()

    def test_empty_repository(self):
        pass

    def test_empty(self):
        mr = Storage("hdf5", "test.h5").morphologies
        m = mr.load("M")
        msg = "Empty morfo should not have root branches"
        self.assertEqual(0, len(m.roots), msg)
        msg = "Empty morfo should not have branches"
        self.assertEqual(0, len(m.branches), msg)
        msg = "Empty morfo should not have points"
        self.assertEqual(0, len(m.flatten()), msg)
        self.assertEqual(0, len(m), msg)
        self.assertTrue(m._check_shared(), "Empty morpho not shared")

    def test_empty_branches(self):
        mr = Storage("hdf5", "test2.h5").morphologies
        m = mr.load("M")
        msg = "Empty unattached branches should still be root."
        self.assertEqual(3, len(m.roots), msg)
        self.assertEqual(3, len(m.branches), "Missing branch")
        msg = "Empty morfo should not have points, even when it has empty branches"
        self.assertEqual(0, len(m), msg)
        self.assertEqual(0, len(m.flatten()), msg)
        self.assertTrue(m._check_shared(), "Load should produce shared")

    def test_single_branch_single_element(self):
        mr = Storage("hdf5", "test3.h5").morphologies
        m = mr.load("M")
        msg = "Single point unattached branches should still be root."
        self.assertEqual(1, len(m.roots), msg)
        self.assertEqual(1, len(m.branches), "Missing branch")
        msg = "Flatten of single point should produce 1 x 3 matrix."
        self.assertEqual((1, 3), m.flatten().shape, msg)
        msg = "should produce 1 element vector."
        self.assertEqual((1,), m.flatten_radii().shape, msg)
        self.assertEqual((1,), m.flatten_labels().shape, msg)
        msg = "Flatten without properties should produce n x 0 matrix."
        self.assertEqual({}, m.flatten_properties(), msg)

    def test_multi_branch_single_element(self):
        mr = Storage("hdf5", "test4.h5").morphologies
        m = mr.load("M")
        msg = "Single point unattached branches should still be root."
        self.assertEqual(5, len(m.roots), msg)
        self.assertEqual(5, len(m.branches), "Missing branch")
        msg = "Flatten of single point branches should produce n-branch x n-vectors matrix."
        matrix = m.flatten()
        self.assertEqual((5, 3), matrix.shape, msg)
        msg = "Flatten produced an incorrect matrix"
        self.assertTrue(
            np.array_equal(np.array([[i * 2] * 3 for i in range(5)]), matrix), msg
        )

    def test_multi_branch_single_element_depth_first(self):
        mr = Storage("hdf5", "test5.h5").morphologies
        m = mr.load("M")
        msg = "1 out of 5 branches was attached, 4 roots expected."
        self.assertEqual(4, len(m.roots), msg)
        self.assertEqual(5, len(m.branches), "Missing branch")
