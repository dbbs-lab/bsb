import unittest

from bsb import Scaffold, WorkflowError
from bsb_test import FixedPosConfigFixture, NumpyTestCase, RandomStorageFixture

from bsb_hdf5.connectivity_set import LocationOutOfBoundsError


class TestConnectivitySet(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg.connectivity.add(
            "all_to_all",
            dict(
                strategy="bsb.connectivity.AllToAll",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["test_cell"]),
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile(clear=True, skip_connectivity=True)

    def test_pre_oob(self):
        f = self.network.connectivity.all_to_all.connect_cells

        def pre_oob_connect(pre_set, post_set, src_locs, dest_locs, tag=None):
            f(pre_set, post_set, src_locs + [100, 0, 0], dest_locs + [100, 0, 0])

        self.network.connectivity.all_to_all.connect_cells = pre_oob_connect
        with self.assertRaises(WorkflowError) as wfe:
            self.network.compile(append=True, skip_placement=True)
        if self.network.is_main_process():
            self.assertEqual(
                type(wfe.exception.exceptions[0].error), LocationOutOfBoundsError
            )
