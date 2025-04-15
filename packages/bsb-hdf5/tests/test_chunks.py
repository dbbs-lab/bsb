import unittest

import numpy as np
from bsb import Chunk, Scaffold
from bsb_test import NumpyTestCase, RandomStorageFixture, skip_parallel, timeout
from bsb_test.configs import get_test_config


class TestChunks(
    RandomStorageFixture, unittest.TestCase, NumpyTestCase, engine_name="hdf5"
):
    @skip_parallel
    @timeout(3)
    # Single process; this does not test any parallel read/write validity, just the
    # basic chunk properties
    def test_default_chunk(self):
        # Test that when we don't specify a chunk the default is to read all chunks

        # Use the single chunk test to generate a network with some data in the default
        # (0,0,0) chunk and some data the other test is supposed to ignore in chunk 001
        self.test_single_chunk()
        # Continue using this network, checking that we pick up on the data in chunk 001
        chunk0 = self.ps.load_positions()
        # Unloaded the chunks loaded by the other test. The desired behavior is then to
        # read all chunks.
        self.ps.exclude_chunk(Chunk((0, 0, 0), None))
        chunk_all = self.ps.load_positions()
        self.assertGreater(len(chunk_all), len(chunk0))

    @skip_parallel
    @timeout(3)
    # Single process; this does not test any parallel read/write validity, just the
    # basic chunk properties. For example uses `.place` directly.
    def test_single_chunk(self):
        # Test that specifying a single chunk only reads the data from that chunk
        cfg = get_test_config("single")
        self.network = network = Scaffold(
            get_test_config("single"), self.storage, clear=True
        )
        self.ps = ps = network.get_placement_set("test_cell")
        ps.include_chunk(Chunk((0, 0, 0), None))
        pos = ps.load_positions()
        self.assertEqual(0, len(pos), "Cell pos found before cell placement. Cleared?")
        p = network.placement.test_placement
        cs = network.network.chunk_size
        p.place(Chunk(np.array([0, 0, 0]), cs), p.get_indicators())
        pos = ps.load_positions()
        self.assertGreater(len(pos), 0, "No data loaded from chunk 000 after placement")
        # Force the addition of garbage data in another chunk, to be ignored by this
        # PlacementSet as it is set to load data only from chunk (0,0,0)
        ps.append_data(Chunk((0, 0, 1), None), [0])
        pos2 = ps.load_positions()
        self.assertEqual(
            pos.tolist(), pos2.tolist(), "PlacementSet loaded extraneous chunk data"
        )
