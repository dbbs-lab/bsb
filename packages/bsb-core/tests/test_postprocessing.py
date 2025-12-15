import os
import unittest

import numpy as np
from bsb_test import NumpyTestCase, RandomStorageFixture

from bsb import (
    MPI,
    AfterConnectivityHook,
    AfterPlacementHook,
    Configuration,
    ConnectivityError,
    Scaffold,
    WorkflowError,
    config,
)
from bsb.postprocessing import _merge_sets


class TestAfterConnectivityHook(
    RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    def setUp(self):
        super().setUp()

        @config.node
        class TestAfterConn(AfterConnectivityHook):
            def postprocess(self):
                with open(f"test_after_conn_{MPI.get_rank()}.txt", "a") as f:
                    # make sure we have access to the scaffold context
                    f.write(f"{self.scaffold.configuration.name}\n")

        self.network = Scaffold(
            config=Configuration.default(
                name="Test config",
                after_connectivity={"test_after_conn": TestAfterConn()},
            ),
            storage=self.storage,
        )

    def test_after_connectivity_job(self):
        self.network.compile()
        if MPI.get_rank() == 0:
            count_files = 0
            for filename in os.listdir():
                if filename.startswith("test_after_conn_"):
                    count_files += 1
                    with open(filename) as f:
                        lines = f.readlines()
                        self.assertEqual(
                            len(lines), 1, "The postprocess should be called only once."
                        )
                        self.assertEqual(lines[0], "Test config\n")
                    os.remove(filename)
            self.assertEqual(count_files, 1)


class TestAfterPlacementHook(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    def setUp(self):
        super().setUp()

        @config.node
        class TestAfterPlace(AfterPlacementHook):
            def postprocess(self):
                with open(f"test_after_place_{MPI.get_rank()}.txt", "a") as f:
                    # make sure we have access to the scaffold context
                    f.write(f"{self.scaffold.configuration.name}\n")

        self.network = Scaffold(
            config=Configuration.default(
                name="Test config",
                after_placement={"test_after_placement": TestAfterPlace()},
            ),
            storage=self.storage,
        )

    def test_after_placement_job(self):
        self.network.compile()
        if MPI.get_rank() == 0:
            count_files = 0
            for filename in os.listdir():
                if filename.startswith("test_after_place_"):
                    count_files += 1
                    with open(filename) as f:
                        lines = f.readlines()
                        self.assertEqual(
                            len(lines), 1, "The postprocess should be called only once."
                        )
                        self.assertEqual(lines[0], "Test config\n")
                    os.remove(filename)
            self.assertEqual(count_files, 1)


class TestFuseConnectionsHook(
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg = Configuration.default(
            network={"x": 100.0, "y": 100.0, "z": 100.0, "chunk_size": [100, 100, 50]},
            regions={
                "brain_region": {
                    "type": "stack",
                    "children": ["base_layer", "top_layer"],
                }
            },
            partitions=dict(
                base_layer=dict(type="layer", thickness=50),
                top_layer=dict(type="layer", thickness=50),
            ),
            cell_types=dict(
                A=dict(spatial=dict(radius=1, count=2)),
                B=dict(spatial=dict(radius=1, count=4)),
                C=dict(spatial=dict(radius=1, count=2)),
                D=dict(spatial=dict(radius=1, count=3)),
            ),
            placement=dict(
                top_placement={
                    "strategy": "bsb.placement.RandomPlacement",
                    "cell_types": ["B", "D"],
                    "partitions": ["top_layer"],
                },
                base_placement={
                    "strategy": "bsb.placement.RandomPlacement",
                    "cell_types": ["A"],
                    "partitions": ["base_layer"],
                },
                other_placement={
                    "strategy": "bsb.placement.RandomPlacement",
                    "cell_types": ["C"],
                    "partitions": ["base_layer"],
                },
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile(skip_connectivity=True)

        # Set custom connections only on master rank
        a_to_b = -1 * np.ones((2, 4, 3))
        a_to_b[0] = [[0, 1, 1], [1, 1, 1], [1, 2, 1], [1, 2, 2]]
        a_to_b[1, :, 0] = [0, 0, 1, 2]

        b_to_c = -1 * np.ones((2, 4, 3))
        b_to_c[0, :, 0] = [0, 0, 1, 3]
        b_to_c[1, :, 0] = [0, 1, 0, 1]

        c_to_d = -1 * np.ones((2, 5, 3))
        c_to_d[0, :, 0] = [0, 0, 1, 1, 1]
        c_to_d[1] = [[0, 2, 1], [2, -1, -1], [0, 1, 1], [1, -1, -1], [2, 1, 2]]

        b_to_d = -1 * np.ones((2, 2, 3))
        b_to_d[0, :, 0] = [0, 3]
        b_to_d[1, :, 0] = [1, 0]

        d_to_a = -1 * np.ones((2, 1, 3))
        d_to_a[0, :, 0] = [0]
        d_to_a[1, :, 0] = [0]

        self.a_to_b = a_to_b
        self.b_to_c = b_to_c
        self.c_to_d = c_to_d
        self.b_to_d = b_to_d
        if not MPI.get_rank():
            ps_a = self.network.cell_types["A"].get_placement_set()
            ps_b = self.network.cell_types["B"].get_placement_set()
            ps_c = self.network.cell_types["C"].get_placement_set()
            ps_d = self.network.cell_types["D"].get_placement_set()

            self.network.connect_cells(ps_a, ps_b, a_to_b[0], a_to_b[1], "A_to_B")
            self.network.connect_cells(ps_b, ps_c, b_to_c[0], b_to_c[1], "B_to_C")
            self.network.connect_cells(ps_c, ps_d, c_to_d[0], c_to_d[1], "C_to_D")
            self.network.connect_cells(ps_b, ps_d, b_to_d[0], b_to_d[1], "B_to_D")
            self.network.connect_cells(ps_d, ps_a, d_to_a[0], d_to_a[1], "D_to_A")

    def test_nonexistent_set(self):
        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["B_to_C", "K_to_B"],
            )
        )

        with self.assertRaises(WorkflowError) as e:
            self.network.run_after_connectivity()
        if self.network.is_main_process():
            self.assertIsInstance(e.exception.exceptions[0].error, ConnectivityError)

    def test_merge_sets(self):
        computed_connections = _merge_sets(self.a_to_b, self.b_to_c)
        real_connections = (
            np.array([[0, 1, 1], [0, 1, 1], [1, 1, 1], [1, 1, 1], [1, 2, 1]]),
            np.array([[0, -1, -1], [1, -1, -1], [0, -1, -1], [1, -1, -1], [0, -1, -1]]),
        )

        self.assertAll(
            computed_connections[0] == real_connections[0],
            "Fused connection must match real connections",
        )
        self.assertAll(
            computed_connections[1] == real_connections[1],
            "Fused connection must match real connections",
        )

    def test_wrong_chains(self):
        # Test that discontinuous trees is detected

        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["A_to_B", "C_to_D"],
            )
        )

        with self.assertRaises(WorkflowError) as e:
            self.network.run_after_connectivity()
        if self.network.is_main_process():
            self.assertIsInstance(e.exception.exceptions[0].error, ValueError)

    def test_multiple_ends(self):
        """Will test that the connectivity A > B > ( C+ D ) are merged in
        A > D and A > C"""
        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["B_to_C", "B_to_D", "A_to_B"],
            )
        )
        self.network.run_after_connectivity()
        a_to_d = self.network.get_connectivity_set("A_to_D")
        a_to_c = self.network.get_connectivity_set("A_to_C")

        computed_a_to_d = a_to_d.load_connections().all()
        computed_a_to_c = a_to_c.load_connections().all()
        real_a_to_c = (
            [[0, 1, 1], [1, 1, 1], [1, 2, 1], [0, 1, 1], [1, 1, 1]],
            [[0, -1, -1], [0, -1, -1], [0, -1, -1], [1, -1, -1], [1, -1, -1]],
        )
        real_a_to_d = ([[0, 1, 1], [1, 1, 1]], [1, -1, -1], [1, -1, -1])
        self.assertAll(
            (real_a_to_c[0] == computed_a_to_c[0])
            & (real_a_to_c[1] == computed_a_to_c[1]),
            "A_to_C set not properly computed!",
        )
        self.assertAll(
            (real_a_to_d[0] == computed_a_to_d[0])
            & (real_a_to_d[1] == computed_a_to_d[1]),
            "A_to_D set not properly computed!",
        )

    def test_multiple_roots(self):
        """Will test that the connectivity (C + B) > D > A are merged
        in C > A and B > A"""
        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["D_to_A", "C_to_D", "B_to_D"],
            )
        )
        self.network.run_after_connectivity()
        cs = self.network.get_connectivity_set("B_to_A")
        c_to_a = self.network.get_connectivity_set("C_to_A")

        real_b_to_a = ([3, -1, -1], [0, -1, -1])
        computed_b_to_a = cs.load_connections().all()
        real_c_to_a = ([[0, -1, -1], [1, -1, -1]], [[0, -1, -1], [0, -1, -1]])
        computed_c_to_a = c_to_a.load_connections().all()

        self.assertAll(
            (real_b_to_a[0] == computed_b_to_a[0])
            & (real_b_to_a[1] == computed_b_to_a[1]),
            "B_to_A set not properly computed!",
        )
        self.assertAll(
            (real_c_to_a[0] == computed_c_to_a[0])
            & (real_c_to_a[1] == computed_c_to_a[1]),
            "C_to_A set not properly computed!",
        )

    def test_with_branches(self):
        """Will test that the connections A > B > C > D +
        A > B > D are merged in A > D"""
        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["A_to_B", "B_to_C", "C_to_D", "B_to_D"],
            )
        )
        self.network.run_after_connectivity()
        D_locs = self.c_to_d[1]
        predicted_connections = (
            np.concatenate(
                [
                    np.repeat(self.a_to_b[0, 0:3:], [5, 5, 2], axis=0),
                    self.a_to_b[0, 0:2],
                ],
                axis=0,
            ),
            np.concatenate(
                [
                    np.append(
                        np.concatenate((D_locs, D_locs), axis=0), D_locs[0:2], axis=0
                    ),
                    np.repeat([self.b_to_d[1, 0]], 2, axis=0),
                ],
                axis=0,
            ),
        )
        cs = self.network.get_connectivity_set("new_connection")
        computed_connections = cs.load_connections().all()
        self.assertEqual(len(computed_connections[0]), len(predicted_connections[0]))
        ids_found = []
        for src, tgt in zip(*predicted_connections, strict=False):
            ids = np.where(
                np.all(src == computed_connections[0], axis=-1)
                * np.all(tgt == computed_connections[1], axis=-1)
            )[0]
            ids = ids[np.isin(ids, ids_found, invert=True)]
            self.assertGreater(
                len(ids), 0, f"Predicted connection {src}, {tgt} not found"
            )
            ids_found.append(ids[0])

    def test_no_loops(self):
        # Test that a loop is detected

        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["A_to_B", "B_to_C", "D_to_A", "C_to_D"],
            )
        )
        with self.assertRaises(WorkflowError) as e:
            self.network.run_after_connectivity()
        if self.network.is_main_process():
            self.assertIsInstance(e.exception.exceptions[0].error, ConnectivityError)

    def test_three_connectivities(self):
        """Will test that the connections A > B > C > D  are fused in
        A > D"""

        self.cfg.after_connectivity = dict(
            new_connection=dict(
                strategy="merge_connections",
                connections=["B_to_C", "A_to_B", "C_to_D"],
            )
        )
        self.network.run_after_connectivity()

        A_locs = [[0, 1, 1], [1, 1, 1], [1, 2, 1], [1, 2, 2]]
        D_locs = self.c_to_d[1]

        real_connections = (
            (np.repeat(A_locs[0:3:], [5, 5, 2], axis=0)),
            np.append(np.concatenate((D_locs, D_locs), axis=0), D_locs[0:2], axis=0),
        )
        cs = self.network.get_connectivity_set("new_connection")
        computed_connections = cs.load_connections().all()

        self.assertEqual(
            len(computed_connections[0]),
            len(computed_connections[1]),
            "Lenghts of pre_locs and post_locs connections do not match!",
        )
        self.assertEqual(
            len(computed_connections[0]),
            len(real_connections[0]),
            "Number of computed connections do not match the number of real connections",
        )

        # Create a transpose of the arrays and check if we obtain the same connections

        reversed_comp = np.array(
            [
                (ele[0], ele[1])
                for ele in zip(
                    computed_connections[0], computed_connections[1], strict=False
                )
            ]
        )
        reversed_real = np.array(
            [
                (ele[0], ele[1])
                for ele in zip(real_connections[0], real_connections[1], strict=False)
            ]
        )

        check_all = np.zeros(len(reversed_real))
        for i, real in enumerate(reversed_real):
            for comp in reversed_comp:
                check_all[i] += np.all(real == comp)

        self.assertAll(check_all == 1, "Some fused connections do not match real ones!")

    def test_intermediate_removal(self):
        """This test remove cell B from the connectivity tree,
        A > B > (C + D) is fused in A > C and A > D"""
        self.cfg.after_connectivity = dict(
            new_connection=dict(strategy="intermediate_removal", cell_list=["B"])
        )
        self.network.run_after_connectivity()
        a_to_d = self.network.get_connectivity_set("A_to_D")
        a_to_c = self.network.get_connectivity_set("A_to_C")

        computed_a_to_d = a_to_d.load_connections().all()
        computed_a_to_c = a_to_c.load_connections().all()
        real_a_to_c = (
            [[0, 1, 1], [1, 1, 1], [1, 2, 1], [0, 1, 1], [1, 1, 1]],
            [[0, -1, -1], [0, -1, -1], [0, -1, -1], [1, -1, -1], [1, -1, -1]],
        )
        real_a_to_d = ([[0, 1, 1], [1, 1, 1]], [[1, -1, -1], [1, -1, -1]])
        self.assertAll(
            (real_a_to_c[0] == computed_a_to_c[0])
            & (real_a_to_c[1] == computed_a_to_c[1]),
            "A_to_C set not properly computed!",
        )
        self.assertAll(
            (real_a_to_d[0] == computed_a_to_d[0])
            & (real_a_to_d[1] == computed_a_to_d[1]),
            "A_to_D set not properly computed!",
        )

    def test_removal_of_two(self):
        self.cfg.after_connectivity = dict(
            new_connection=dict(strategy="intermediate_removal", cell_list=["C", "A"])
        )
        self.network.run_after_connectivity()
        b_to_d = self.network.get_connectivity_set("B_to_D")
        d_to_b = self.network.get_connectivity_set("D_to_B")
        real_b_to_d = (
            [
                [3, -1, -1],
                [0, -1, -1],
                [0, -1, -1],
                [0, -1, -1],
                [1, -1, -1],
                [3, -1, -1],
                [0, -1, -1],
                [3, -1, -1],
                [0, -1, -1],
                [0, -1, -1],
                [1, -1, -1],
                [3, -1, -1],
            ],
            [
                [0, -1, -1],
                [1, -1, -1],
                [0, 2, 1],
                [0, 1, 1],
                [0, 2, 1],
                [0, 1, 1],
                [1, -1, -1],
                [1, -1, -1],
                [2, -1, -1],
                [2, 1, 2],
                [2, -1, -1],
                [2, 1, 2],
            ],
        )
        real_d_to_b = ([0, -1, -1], [0, -1, -1])
        computed_b_to_d = b_to_d.load_connections().all()
        computed_d_to_b = d_to_b.load_connections().all()
        self.assertAll(
            (real_b_to_d[0] == computed_b_to_d[0])
            & (real_b_to_d[1] == computed_b_to_d[1]),
            "A_to_D set not properly computed!",
        )
        self.assertAll(
            (real_d_to_b[0] == computed_d_to_b[0])
            & (real_d_to_b[1] == computed_d_to_b[1]),
            "D_to_B set not properly computed!",
        )

    def test_intrem_loop(self):
        """From our tree A > B > D > A if we remove both D and A
        a loop should be detected"""
        self.cfg.after_connectivity = dict(
            new_connection=dict(strategy="intermediate_removal", cell_list=["D", "A"])
        )
        with self.assertRaises(WorkflowError) as e:
            self.network.run_after_connectivity()
        if self.network.is_main_process():
            self.assertIsInstance(e.exception.exceptions[0].error, ConnectivityError)
