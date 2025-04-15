import unittest

import numpy as np
from bsb_test.engines import TestConnectivitySet as _TestConnectivitySet
from bsb_test.engines import TestMorphologyRepository as _TestMorphologyRepository
from bsb_test.engines import TestPlacementSet as _TestPlacementSet
from bsb_test.engines import TestStorage as _TestStorage


class TestStorage(_TestStorage, unittest.TestCase, engine_name="hdf5"):
    pass


class TestPlacementSet(_TestPlacementSet, unittest.TestCase, engine_name="hdf5"):
    def test_convert_to_local(self):
        self.network.compile()
        ps = self.network.get_placement_set("test_cell")
        # Def a list of ids
        glob_ids = [0, 3, 44, 77, 25]
        # Now we select to work on 2nd and 4th chunk only ( ordering is made on chunk id)
        ps.set_chunk_filter([(1, 0, 0), (1, 0, 1)])
        local_ids = ps.convert_to_local(glob_ids)
        self.assertAll(
            local_ids == np.array([19, 27, 0]),
            " [0,3] should have been discarded, [44,77,25] should have been converted to [19,27,0]",
        )
        # test when the selected chunks do not have any of the cell ids
        ps.set_chunk_filter([(0, 0, 1)])
        local_ids = ps.convert_to_local(glob_ids)
        # Get pop size of 3rd chunk
        pop_size = ps.get_chunk_stats()[str(self.chunks[1].id)]
        res_array = np.full(pop_size, False)
        self.assertAll(
            local_ids == res_array,
            "If selected chunk has no one of the ids it should return an array of pop_size size filled with False values",
        )


class TestMorphologyRepository(
    _TestMorphologyRepository, unittest.TestCase, engine_name="hdf5"
):
    pass


class TestConnectivitySet(_TestConnectivitySet, unittest.TestCase, engine_name="hdf5"):
    pass
