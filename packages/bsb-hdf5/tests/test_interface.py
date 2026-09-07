import unittest

import numpy as np
from bsb import CellType, Chunk
from bsb_test import skip_parallel
from bsb_test.engines import TestConnectivitySet as _TestConnectivitySet
from bsb_test.engines import TestMorphologyRepository as _TestMorphologyRepository
from bsb_test.engines import TestPlacementSet as _TestPlacementSet
from bsb_test.engines import TestStorage as _TestStorage


class TestStorage(_TestStorage, unittest.TestCase, engine_name="hdf5"):
    pass


class TestPlacementSet(_TestPlacementSet, unittest.TestCase, engine_name="hdf5"):
    @skip_parallel
    def test_len_of_entities(self):
        # Entities carry no positional data, so their length can only come from the
        # count tracked on the placement set, never from the position datasets.
        ct = CellType(name="entity_cell", entity=True, spatial=dict(count=12))
        ps = self.storage.require_placement_set(ct)
        ps.append_entities(Chunk((0, 0, 0), self.chunk_size), 7)
        ps.append_entities(Chunk((0, 0, 1), self.chunk_size), 5)
        self.assertEqual(12, len(ps), "len should count the placed entities")
        self.assertEqual(len(ps.load_ids()), len(ps), "len should match the id count")
        ps.set_chunk_filter([self.chunks[1]])
        self.assertEqual(5, len(ps), "entity len should respect the chunk filter")
        self.assertEqual(len(ps.load_ids()), len(ps), "len should match the id count")

    def test_len_of_chunk_filter(self):
        self.network.compile()
        ps = self.network.get_placement_set("test_cell")
        self.assertEqual(100, len(ps), "len should count every chunk")
        ps.set_chunk_filter(self.chunks[:2])
        self.assertEqual(50, len(ps), "len should count only the filtered chunks")
        self.assertEqual(len(ps.load_ids()), len(ps), "len should match the id count")
        self.assertEqual(
            len(ps.load_positions()), len(ps), "len should match the loaded positions"
        )
        ps.clear_chunk_filter()
        self.assertEqual(100, len(ps), "len should count every chunk again")

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
            " [0,3] should have been discarded, "
            "[44,77,25] should have been converted to [19,27,0]",
        )
        # test when the selected chunks do not have any of the cell ids
        ps.set_chunk_filter([(0, 0, 1)])
        local_ids = ps.convert_to_local(glob_ids)
        # Get pop size of 3rd chunk
        pop_size = ps.get_chunk_stats()[str(self.chunks[1].id)]
        res_array = np.full(pop_size, False)
        self.assertAll(
            local_ids == res_array,
            "If selected chunk has no one of the ids "
            "it should return an array of pop_size size filled with False values",
        )


class TestMorphologyRepository(
    _TestMorphologyRepository, unittest.TestCase, engine_name="hdf5"
):
    pass


class TestConnectivitySet(_TestConnectivitySet, unittest.TestCase, engine_name="hdf5"):
    pass
