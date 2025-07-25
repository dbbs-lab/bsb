import unittest

from bsb_test import (
    FixedPosConfigFixture,
    MorphologiesFixture,
    NetworkFixture,
    NumpyTestCase,
    RandomStorageFixture,
)

from bsb import Configuration, DatasetNotFoundError, Scaffold
from bsb.connectivity import (
    MorphologyToShapeIntersection,
    ShapeToMorphologyIntersection,
    ShapeToShapeIntersection,
)


class TestShapeConnectivity(
    RandomStorageFixture,
    FixedPosConfigFixture,
    NetworkFixture,
    MorphologiesFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
    morpho_filters=["2branch"],
):
    def setUp(self):
        super().setUp()

        self.cfg = Configuration.default(
            cell_types=dict(
                test_cell_morpho=dict(
                    spatial=dict(
                        radius=1, density=1, morphologies=[dict(names=["2branch"])]
                    )
                ),
                test_cell_pc_1=dict(spatial=dict(radius=1, density=1)),
                test_cell_pc_2=dict(spatial=dict(radius=1, density=1)),
            ),
            placement=dict(
                fixed_pos_morpho=dict(
                    strategy="bsb.placement.FixedPositions",
                    cell_types=["test_cell_morpho"],
                    partitions=[],
                    positions=[[0, 0, 0], [0, 0, 100], [50, 0, 0], [0, -100, 0]],
                ),
                fixed_pos_pc_1=dict(
                    strategy="bsb.placement.FixedPositions",
                    cell_types=["test_cell_pc_1"],
                    partitions=[],
                    positions=[[40, 40, 40]],
                ),
                fixed_pos_pc_2=dict(
                    strategy="bsb.placement.FixedPositions",
                    cell_types=["test_cell_pc_2"],
                    partitions=[],
                    positions=[[0, -100, 0]],
                ),
            ),
        )

        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile(skip_connectivity=True)

    def test_shape_to_shape(self):
        voxel_size = 25
        config_sphere = dict(type="sphere", radius=40.0, origin=[0, 0, 0])
        ball_shape = {
            "voxel_size": voxel_size,
            "shapes": [config_sphere],
            "labels": [["sphere"]],
        }
        # All the points of the presyn shape are inside the postsyn shape
        self.network.connectivity["shape_to_shape_1"] = ShapeToShapeIntersection(
            presynaptic=dict(
                cell_types=["test_cell_pc_1"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            postsynaptic=dict(
                cell_types=["test_cell_pc_1"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            affinity=0.9,
            pruning_ratio=0.1,
        )

        # There are no intersections between the presyn and postsyn shapes
        self.network.connectivity["shape_to_shape_2"] = ShapeToShapeIntersection(
            presynaptic=dict(
                cell_types=["test_cell_pc_1"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            postsynaptic=dict(
                cell_types=["test_cell_pc_2"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            affinity=0.9,
            pruning_ratio=0.1,
        )

        self.network.compile(skip_placement=True, append=True)

        cs = self.network.get_connectivity_set("shape_to_shape_1")
        con = cs.load_connections().all()[0]
        intersection_points = len(con)
        self.assertGreater(
            intersection_points,
            0,
            "expected at least one intersection point",
        )

        with self.assertRaises(DatasetNotFoundError):
            # No connectivity set expected because no overlap of the populations' chunks.
            self.network.get_connectivity_set("shape_to_shape_2")

    def test_shape_to_morpho(self):
        voxel_size = 25
        config_sphere = dict(type="sphere", radius=40.0, origin=[0, 0, 0])
        ball_shape = {
            "voxel_size": voxel_size,
            "shapes": [config_sphere],
            "labels": [["sphere"]],
        }

        # We know a priori that there are intersections between the presyn shape
        # and the morphology
        self.network.connectivity["shape_to_morpho_1"] = ShapeToMorphologyIntersection(
            presynaptic=dict(
                cell_types=["test_cell_pc_2"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            postsynaptic=dict(cell_types=["test_cell_morpho"]),
            affinity=0.5,
            pruning_ratio=0.5,
        )

        # There are no intersections between the presyn shape and the morpho
        self.network.connectivity["shape_to_morpho_2"] = ShapeToMorphologyIntersection(
            presynaptic=dict(
                cell_types=["test_cell_pc_1"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            postsynaptic=dict(cell_types=["test_cell_morpho"]),
            affinity=0.5,
            pruning_ratio=0.5,
        )

        self.network.compile(skip_placement=True, append=True)

        cs = self.network.get_connectivity_set("shape_to_morpho_1")
        con = cs.load_connections().all()[0]
        intersection_points = len(con)
        self.assertGreater(
            intersection_points, 0, "expected at least one intersection point"
        )

        cs = self.network.get_connectivity_set("shape_to_morpho_2")
        con = cs.load_connections().all()[0]
        intersection_points = len(con)
        self.assertClose(0, intersection_points, "expected no intersection points")

    def test_morpho_to_shape(self):
        voxel_size = 25
        config_sphere = dict(type="sphere", radius=40.0, origin=[0, 0, 0])
        ball_shape = {
            "voxel_size": voxel_size,
            "shapes": [config_sphere],
            "labels": [["sphere"]],
        }

        # We know a priori that there are intersections between the presyn shape
        # and the morphology
        self.network.connectivity["shape_to_morpho_1"] = MorphologyToShapeIntersection(
            postsynaptic=dict(
                cell_types=["test_cell_pc_2"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            presynaptic=dict(cell_types=["test_cell_morpho"]),
            affinity=0.5,
            pruning_ratio=0.5,
        )

        # There are no intersections between the presyn shape and the morphology.
        self.network.connectivity["shape_to_morpho_2"] = MorphologyToShapeIntersection(
            postsynaptic=dict(
                cell_types=["test_cell_pc_1"],
                shapes_composition=ball_shape,
                morphology_labels=["soma"],
            ),
            presynaptic=dict(cell_types=["test_cell_morpho"]),
            affinity=0.5,
            pruning_ratio=0.5,
        )

        self.network.compile(skip_placement=True, append=True)

        cs = self.network.get_connectivity_set("shape_to_morpho_1")
        con = cs.load_connections().all()[0]
        intersection_points = len(con)
        self.assertGreater(
            intersection_points, 0, "expected at least one intersection point"
        )

        cs = self.network.get_connectivity_set("shape_to_morpho_2")
        con = cs.load_connections().all()[0]
        intersection_points = len(con)
        self.assertClose(0, intersection_points, "expected no intersection points")
