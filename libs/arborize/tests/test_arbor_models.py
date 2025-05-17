import unittest
from itertools import zip_longest

import arbor

from arborize import Schematic, arbor_build
from arborize.builders._arbor import get_decor, get_label_dict, hash_labelset

from ._shared import SchematicsFixture


class TestModelBuilding(SchematicsFixture, unittest.TestCase):
    def setUp(self):
        super().setUp()
        self.schematic = self.p75_pas
        self.cell = arbor_build(self.schematic)

    def test_arbor_build_morphology(self):
        branch_endpoints = {}
        for bid, branch in enumerate(self.schematic.cables):
            ptid = branch_endpoints[branch.parent] if branch.parent else arbor.mnpos
            branch_endpoints[branch] = ptid

        assert (
            len(self.schematic.cables) == self.schematic.arbor.morphology.num_branches
        )
        keys = [*branch_endpoints.keys()]

        def pid(i):
            try:
                return keys.index(i)
            except ValueError:
                # Value for no parent in Arbor
                return arbor.mnpos

        n_branches = 0
        n_points = 0
        # Assert that the data was transferred correctly.
        for bid, vb in enumerate(self.schematic.cables):
            n_branches += 1
            self.assertEqual(
                pid(vb.parent),
                self.schematic.arbor.morphology.branch_parent(bid),
                "Parent error",
            )
            segments = self.schematic.arbor.morphology.branch_segments(bid)
            pwlin = arbor.place_pwlin(self.schematic.arbor.morphology)
            self.assertEqual(
                len(vb.points) - 1, len(segments), "Incorrect amount of points"
            )
            noner = False
            for pt, seg in zip_longest(vb.points, segments):
                n_points += 1
                if seg is None:
                    self.assertFalse(noner, "there should only be 1 point extra")
                    if not noner:
                        noner = True
                        continue
                self.assertEqual(_mkpt(pt), seg.prox, "Coordinate error")
                self.assertLess(pwlin.closest(*pt.coords)[1], 1e-8, "Closeness error")
            self.assertTrue(noner, "there should be 1 less segment than point")

        self.assertEqual(len(self.schematic.cables), n_branches)
        self.assertEqual(sum(len(c.points) for c in self.schematic.cables), n_points)

    def test_arbor_build_ion_painting(self):
        decor = get_decor(self.schematic)
        paintings = {str(p) for p in decor.paintings()}
        # todo: drop when units are released
        # Support pre-units occurences of `scalar`
        value = "(scalar 10)" if "scalar" in str(paintings) else "10"
        self.assertIn(f"('(region \"soma\")', cao={value})", paintings)
        self.assertIn(f"('(region \"soma\")', eca={value})", paintings)
        self.assertIn(f"('(region \"soma\")', cai={value})", paintings)

    def test_arbor_build_cable_painting(self):
        decor = get_decor(self.schematic)
        paintings = {str(p) for p in decor.paintings()}
        # todo: drop when units are released
        # Support pre-units occurences of `scalar`
        Ra = "(scalar 10)" if "scalar" in str(paintings) else "10"
        cm = "(scalar 1)" if "scalar" in str(paintings) else "1"
        self.assertIn(f"('(region \"apical_dendrite\")', Ra{Ra})", paintings)
        self.assertIn(f"('(region \"apical_dendrite\")', Cm={cm})", paintings)

    def test_arbor_build_mech_painting(self):
        decor = get_decor(self.schematic)
        pas = [
            (label, mech.mech.values)
            for label, mech in decor.paintings()
            if isinstance(mech, arbor.density) and mech.mech.name == "pas"
        ]
        self.assertEqual([('(region "soma")', {"e": -70, "g": 0.01})], pas)


class TestModelLabelDict(unittest.TestCase):
    def assertDictEqual(self, d1, d2, msg: str = None):
        return super().assertDictEqual(dict(d1), dict(d2), msg=msg)

    def test_label_dict_soma(self):
        schematic = Schematic()
        schematic.create_location((0, 0), [0, 0, 0], 1, ["soma"])
        schematic.create_location((0, 1), [0, 0, 1], 1, ["soma"])
        labelsets, label_dict = get_label_dict(schematic)
        self.assertDictEqual({"soma": "(tag 0)"}, label_dict)

    def test_label_dict_soma_endlabel(self):
        schematic = Schematic()
        schematic.create_location((0, 0), [0, 0, 0], 1, ["soma"])
        schematic.create_location((0, 1), [0, 0, 1], 1, ["nonsoma"])
        labelsets, label_dict = get_label_dict(schematic)
        self.assertDictEqual({"soma": "(tag 0)", "nonsoma": "(tag 1)"}, label_dict)

    def test_label_dict_soma_double_label(self):
        schematic = Schematic()
        schematic.create_location((0, 0), [0, 0, 0], 1, ["soma"])
        schematic.create_location((0, 1), [0, 0, 1], 1, ["soma", "nonsoma"])
        labelsets, label_dict = get_label_dict(schematic)
        self.assertDictEqual(
            {"soma": "(join (tag 0) (tag 1))", "nonsoma": "(tag 1)"}, label_dict
        )

    def test_label_dict_hash(self):
        schematic = Schematic()
        schematic.create_location((0, 0), [0, 0, 0], 1, ["soma"])
        schematic.create_location((0, 1), [0, 0, 1], 1, ["soma", "nonsoma"])
        labelsets, label_dict = get_label_dict(schematic)
        self.assertEqual(0, labelsets.get(hash_labelset(["soma"])))
        self.assertEqual(1, labelsets.get(hash_labelset(["nonsoma", "soma"])))
        self.assertEqual(1, labelsets.get(hash_labelset(["nonsoma", "soma"])))


def _mkpt(p: "Point") -> arbor.mpoint:
    return arbor.mpoint(*p.coords, p.radius)
