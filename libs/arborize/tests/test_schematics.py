import unittest

import numpy as np

from arborize import define_model
from arborize.schematics import file_schematic
from tests._shared import SchematicsFixture


class TestFileSchematic(SchematicsFixture, unittest.TestCase):
    def test_labels(self):
        self.assertEqual(
            sorted(["soma", "apical_dendrite", "basal_dendrite"]),
            sorted(set(b.labels[0] for b in self.p75)),
            "Missing or added label types",
        )

    def test_tags(self):
        self.assertEqual(
            sorted(["soma", "tag_7"]),
            sorted(set(b.labels[0] for b in self.cell010)),
            "Missing or added label types",
        )

    def test_multitagged_branch(self):
        # FIXME: When https://github.com/BlueBrain/MorphIO/issues/469 is fixed we can use
        # MorphIO to load SWC files that have multiple different tags on a branch
        pass

    def test_one_branch(self):
        # Expect soma + one branch
        self.assertEqual(2, len(self.one_branch.cables), "expected 2 branches")
        self.assertEqual(
            2, len(self.one_branch.cables[0].points), "expected 2 soma points"
        )
        # Expect the unit branch to be labelled as "soma"
        self.assertEqual(
            ["soma"],
            self.one_branch.cables[0].points[0].branch.labels,
            "expected soma labels on branch 0",
        )
        # Expect 2 + 0 inferred points on the next branch (no point inference on soma)
        self.assertEqual(
            2, len(self.one_branch.cables[1].points), "expected 2 branch points"
        )

    def test_two_branch(self):
        # Expect soma + two branches
        self.assertEqual(3, len(self.two_branch.cables), "expected 3 branches")
        self.assertEqual(
            2, len(self.two_branch.cables[0].points), "expected 2 soma points"
        )
        # Expect the unit branch to be labelled as "soma"
        self.assertEqual(
            ["soma"],
            self.two_branch.cables[0].points[0].branch.labels,
            "expected soma labels on branch 0",
        )
        # Expect 2 + 0 inferred points on the next branch (no point inference on soma)
        self.assertAlmostEqual(
            2, len(self.two_branch.cables[1].points), 5, "expected 2 branch points"
        )
        self.assertAlmostEqual(
            0.3,
            self.two_branch.cables[1].points[0].radius,
            5,
            "incorrect radius",
        )
        self.assertTrue(
            np.array_equal([0.0, 6.0, 0.0], self.two_branch.cables[1].points[0].coords),
            "incorrect coords",
        )
