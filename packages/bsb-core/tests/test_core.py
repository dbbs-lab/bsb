import os
import unittest

from bsb_test import NetworkFixture, RandomStorageFixture, skip_serial, timeout
from mpi4py import MPI

from bsb import Configuration, PlacementSet, Scaffold, Storage, core, get_engine_node


class TestCore(
    RandomStorageFixture, NetworkFixture, unittest.TestCase, engine_name="hdf5"
):
    def setUp(self):
        self.cfg = Configuration.default()
        super().setUp()

    def test_from_storage(self):
        """
        Use the `from_storage` function to load a network.
        """
        self.network.compile(clear=True)
        core.from_storage(self.network.storage.root)

    def test_missing_storage(self):
        with self.assertRaises(FileNotFoundError):
            core.from_storage("does_not_exist")

    def test_set_netw_root_nodes(self):
        """
        Test the anti-pattern of resetting the storage configuration for runtime errors.
        """
        self.network.storage_cfg = {"root": self.network.storage.root, "engine": "hdf5"}

    def test_set_netw_config(self):
        """
        Test resetting the configuration object.
        """
        self.network.configuration = Configuration.default(
            regions=dict(x=dict(children=[]))
        )
        self.assertEqual(1, len(self.network.regions), "setting cfg failed")

    def test_netw_props(self):
        """
        Test the storage engine property keys like `.morphologies` and `.files`
        """
        self.assertEqual(
            0, len(self.network.morphologies.all()), "just checking morph prop"
        )

    def test_resize(self):
        self.network.partitions.add("layer", thickness=100)
        self.network.regions.add("region", children=["layer"])
        # fixme: https://github.com/dbbs-lab/bsb-core/issues/812
        self.network.topology.children.append(self.network.regions.region)
        self.network.resize(x=500, y=500, z=500)
        self.assertEqual(500, self.network.network.x, "resize didnt update network node")
        self.assertEqual(
            500, self.network.partitions.layer.data.width, "didnt resize layer"
        )

    def test_get_placement_sets(self):
        """
        Test that placement sets for cell types are automatically initialized.
        """
        self.network.cell_types.add("my_type", spatial=dict(radius=2, density=1))
        pslist = self.network.get_placement_sets()
        self.assertIsInstance(pslist, list, "should get list of PS")
        self.assertEqual(1, len(pslist), "should have one PS per cell type")
        self.assertIsInstance(pslist[0], PlacementSet, "elements should be PS")

    def test_diagrams(self):
        self.network.cell_types.add("cell1", {"spatial": {"radius": 1, "density": 1}})
        self.network.cell_types.add("cell2", {"spatial": {"radius": 1, "density": 1}})
        self.network.placement.add(
            "p1",
            {
                "strategy": "bsb.placement.FixedPositions",
                "positions": [[0, 0, 0], [1, 1, 1], [2, 2, 2]],
                "cell_types": ["cell1", "cell2"],
                "partitions": [],
            },
        )
        self.network.connectivity.add(
            "a_to_b",
            {
                "strategy": "bsb.connectivity.AllToAll",
                "presynaptic": {"cell_types": ["cell1"]},
                "postsynaptic": {"cell_types": ["cell2"]},
            },
        )
        cfg_diagram = self.network.get_config_diagram()
        self.assertIn('digraph "network"', cfg_diagram)
        self.assertIn('cell1[label="cell1"]', cfg_diagram)
        self.assertIn('cell2[label="cell2"]', cfg_diagram)
        self.assertIn('cell1 -> cell2[label="a_to_b"]', cfg_diagram)
        self.network.compile()
        storage_diagram = self.network.get_storage_diagram()
        self.assertIn('digraph "network"', storage_diagram)
        self.assertIn('cell1[label="cell1 (3 cell1)"]', storage_diagram)
        self.assertIn('cell2[label="cell2 (3 cell2)"]', storage_diagram)
        self.assertIn('cell1 -> cell2[label="a_to_b (9)"]', storage_diagram)

    @skip_serial
    @timeout(3)
    def test_mpi_from_storage(self):
        self.network.compile(clear=True)
        world = MPI.COMM_WORLD
        if world.Get_rank() != 1:
            # we make rank 1 skip while the others would load the network
            group = world.group.Excl([1])
            comm = world.Create_group(group)
            core.from_storage(self.network.storage.root, comm)

    @skip_serial
    @timeout(3)
    def test_mpi_compile(self):
        world = MPI.COMM_WORLD
        if world.Get_rank() != 1:
            # we make rank 1 skip while the others would load the network
            group = world.group.Excl([1])
            comm = world.Create_group(group)
            # Test compile with no storage
            Scaffold(
                Configuration.default(
                    storage=dict(engine="hdf5", root="test_network.hdf5")
                ),
                comm=comm,
            ).compile(clear=True)
            if world.Get_rank() == 0:
                os.remove("test_network.hdf5")
            # Test compile with external storage
            s = Storage("hdf5", get_engine_node("hdf5")(engine="hdf5").root, comm=comm)
            # self.cfg was modified when creating self.network but should update to match
            # the new storage
            Scaffold(self.cfg, storage=s, comm=comm).compile(clear=True)
            s.remove()


class TestProfiling(
    RandomStorageFixture, NetworkFixture, unittest.TestCase, engine_name="hdf5"
):
    def setUp(self):
        self.cfg = Configuration.default()
        super().setUp()

    def test_profiling(self):
        import bsb.profiling

        bsb.options.profiling = True
        self.network.compile()

        self.assertGreater(
            len(bsb.profiling.get_active_session()._meters), 0, "missing meters"
        )
        world = MPI.COMM_WORLD
        if not world.Get_rank():
            found = 0
            for filename in os.listdir():
                if filename.startswith("bsb_profiling_") and filename.endswith(".pkl"):
                    print(filename)
                    found += 1
                    os.remove(filename)
            self.assertEqual(
                found,
                world.Get_size(),
                f"should have found {world.Get_size()} profiling file(s)",
            )
        bsb.options.profiling = False
