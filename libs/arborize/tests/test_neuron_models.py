import os
import unittest

from patch import p

from arborize import Schematic, define_model, neuron_build
from arborize.exceptions import (
    ProxyWarning,
    UnconnectedPointInSpaceWarning,
    UnknownLocationError,
    UnknownSynapseError,
)

# This import only works when tests are executed from root dir.
from tests._shared import SchematicsFixture


@unittest.skipIf(
    "NRN_SEGFAULT" in os.environ,
    "These tests are skipped to test the other tests below separately. See https://github.com/neuronsimulator/nrn/issues/2641",
)
class TestModelBuilding(SchematicsFixture, unittest.TestCase):
    def test_mech_insert(self):
        cell = neuron_build(self.p75_pas)
        self.assertEqual(
            len(self.p75_pas), len(cell.sections), "constructed diff n branches"
        )
        soma = cell.get_sections_with_any_label(["soma"])
        basal = cell.get_sections_with_any_label(["basal_dendrite"])
        apical = cell.get_sections_with_any_label(["apical_dendrite"])
        self.assertTrue(
            all("pas" in [mech.name() for mech in sec(0.5)] for sec in soma),
            "pas not inserted in all soma sections",
        )
        self.assertEqual(-70, soma[0](0.5).pas.e, "Param not set")
        self.assertFalse(
            any("pas" in [mech.name() for mech in sec(0.5)] for sec in basal),
            "pas inserted in some basal sections",
        )
        self.assertFalse(
            any("pas" in [mech.name() for mech in sec(0.5)] for sec in apical),
            "pas inserted in some apical sections",
        )

    def test_synapses(self):
        cell = neuron_build(self.p75_expsyn)
        cell_nosyn = neuron_build(self.p75_expsyn)
        with self.assertRaises(UnknownSynapseError):
            cell.insert_synapse("unknown", (0, 0))
        syn = cell.insert_synapse("ExpSyn", (0, 0))
        with self.assertRaises(UnknownLocationError):
            cell.insert_synapse("ExpSyn", (-1, 0))
        syn.stimulate(start=0, number=3, interval=10)
        r = cell.sections[0].record()
        r_nosyn = cell_nosyn.sections[0].record()
        r2 = p.Vector()
        r2.record(syn._pp.get_segment()._ref_v)

        p.run(100)

        self.assertEqual(list(r), list(r2), "Recording from same loc should be identical")
        self.assertFalse(min(r) == max(r), "No synaptic currents detected")
        self.assertTrue(min(r_nosyn) == max(r_nosyn), "Synaptic currents detected")

    def test_receiver(self):
        cell = neuron_build(self.p75_expsyn)
        cell.insert_receiver(10, "ExpSyn", (0, 0))
        synapse = cell.get_location((0, 0)).section.synapses[0]
        self.assertEqual(synapse.gid, 10, "GId should be 1")
        synapse.stimulate(start=0, number=3, interval=10)
        r = cell.sections[0].record()
        p.run(100)
        self.assertFalse(min(r) == max(r), "No synaptic currents detected")
        cell2 = neuron_build(self.p75_expsyn)
        cell2.insert_receiver(10, "ExpSyn", (0, 0), source="i")
        synapse2 = cell2.get_location((0, 0)).section.synapses[0]
        self.assertEqual(
            synapse2._pp._interpreter.parallel._transfer_max,
            10,
            "transfer_max should be 10",
        )
        synapse2._pp._interpreter.parallel.gid_clear()

    def test_cable_building(self):
        self.cell010.definition = define_model(
            {
                "cable_types": {
                    "soma": {
                        "cable": {"Ra": 102, "cm": 2.1},
                        "ions": {
                            "k": {"rev_pot": -80.993, "int_con": 60, "ext_con": 4},
                            "na": {"rev_pot": 137.5, "int_con": 20, "ext_con": 130},
                        },
                        "mechanisms": {
                            "pas": {"e": -70, "g": 0.01},
                            "hh": {
                                "gnabar": 0,
                                "gkbar": 0.036,
                                "gl": 0.0003,
                                "el": -54.3,
                            },
                        },
                    },
                },
            },
            use_defaults=True,
        )
        cell = neuron_build(self.cell010)
        psection = cell.soma[0].psection()
        density_mechs = psection["density_mechs"]
        ions = psection["ions"]

        # Cable
        self.assertEqual(102, psection["Ra"])
        self.assertEqual(2.1, psection["cm"][0])

        # Mechanisms
        self.assertIn("pas", density_mechs)
        self.assertIn("hh", density_mechs)

        pas = density_mechs["pas"]
        self.assertEqual(-70, pas["e"][0])
        self.assertEqual(0.01, pas["g"][0])

        hh = density_mechs["hh"]
        self.assertEqual(0, hh["gnabar"][0])
        self.assertEqual(0.036, hh["gkbar"][0])
        self.assertEqual(0.0003, hh["gl"][0])
        self.assertEqual(-54.3, hh["el"][0])

        # Ions
        k = ions["k"]
        na = ions["na"]
        self.assertEqual(-80.993, k["ek"][0])
        self.assertEqual(60, k["ki"][0])
        self.assertEqual(4, k["ko"][0])
        self.assertEqual(-80.993, k["ek"][0])
        self.assertEqual(137.5, na["ena"][0])
        self.assertEqual(20, na["nai"][0])
        self.assertEqual(130, na["nao"][0])

    def test_morphology(self):
        cell = neuron_build(self.p75_pas)
        n_locs = sum(len(c.points) for c in self.p75_pas.cables)
        self.assertEqual(len(self.p75_pas.cables), len(cell.sections), "missing cables")
        self.assertEqual(n_locs, sum(s.n3d() for s in cell.sections), "missing locs")


class TestDefinitions(SchematicsFixture, unittest.TestCase):
    def setUp(self):
        self.model = define_model(
            {
                "cable_types": {
                    "soma": {
                        "cable": {"Ra": 102, "cm": 2.1},
                        "ions": {
                            "k": {"rev_pot": -80.993, "int_con": 60, "ext_con": 4},
                            "na": {"rev_pot": 137.5, "int_con": 20, "ext_con": 130},
                        },
                        "mechanisms": {
                            "pas": {"e": -70, "g": 0.01},
                            "hh": {
                                "gnabar": 0,
                                "gkbar": 0.036,
                                "gl": 0.0003,
                                "el": -54.3,
                            },
                        },
                    },
                },
                "synapse_types": {"GABA": {"parameters": {"U": 0.77}}},
            },
            use_defaults=True,
        )

    def test_definitions_copy(self):
        copied_model = self.model.copy()
        self.assertEqual(
            copied_model._synapse_types["GABA"], self.model._synapse_types["GABA"]
        )
        self.assertEqual(
            copied_model._cable_types["soma"].cable,
            self.model._cable_types["soma"].cable,
        )

    def test_definitions_to_dict(self):
        model_dict = self.model.to_dict()
        self.assertEqual(model_dict["synapse_types"]["GABA"]["U"], 0.77)
        self.assertEqual(
            model_dict["cable_types"]["soma"]["ions"]["k"],
            {"rev_pot": -80.993, "int_con": 60, "ext_con": 4},
        )
        self.assertEqual(
            model_dict["cable_types"]["soma"]["ions"]["na"],
            {"rev_pot": 137.5, "int_con": 20, "ext_con": 130},
        )
        self.assertEqual(
            model_dict["cable_types"]["soma"]["cable"],
            {"Ra": 102, "cm": 2.1},
        )
        self.assertEqual(
            model_dict["cable_types"]["soma"]["mechanisms"]["pas"],
            {"e": -70, "g": 0.01},
        )


class TestSinglePointBranchBuilding(unittest.TestCase):
    """
    Test that single point branches in the schematic don't make it to the
    NEURON simulator as a single point section (which are not supported,
    according to a comment in NEURON source code).

    The morphology diagrams in this class work as follows:
    * . denotes a single point branch
    * _ denotes a multi point branch
    * x denotes the subsequent section is not connected and is a root.

    Each column represents a layer of children, each element in the column
    is a child branch of the nearest element in the previous column. The first
    column are the morphology roots.
    """

    def test_empty_unconnected_single_point_warning(self):
        """
        This test verifies that when someone creates a single point in space
        that is not connected to anything, a warning is raised.
        """
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        # .

        # Create single-point-branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])

        with self.assertWarns(UnconnectedPointInSpaceWarning):
            cell = neuron_build(schematic)

        self.assertEqual(len(cell.sections), 0)

    def test_full_unconnected_single_point_warning(self):
        """
        This test verifies that when someone creates a morphology
        that has a single point in space that is not connected to
        anything, a warning is still raised. This test is added to
        ensure the warning works in more complex cases.
        """
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        # . x _

        # Create single-point-branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])

        # Add another branch, not connected to the point
        schematic.create_location((1, 0), (0, 0, 0), 1, ["dendrites"])
        schematic.create_location((1, 1), (1, 1, 0), 1, ["dendrites"])

        with self.assertWarns(UnconnectedPointInSpaceWarning):
            cell = neuron_build(schematic)

        self.assertEqual(len(cell.sections), 1)

    def test_root_with_single_point_children(self):
        """
        This test verifies that when single point branches occur as terminal
        branches, that they are discarded. This test also asserts that proxy
        location accessors behave as expected.
        """
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        # _ .
        #   .

        # Create branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])
        schematic.create_location((0, 1), (1, 0, 0), 1, ["soma"])

        # Add 2 single-point branches as children of branch 0
        schematic.create_location((1, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(0, 1))
        schematic.create_location((2, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(0, 1))

        cell = neuron_build(schematic)

        # Assert only 1 section was created (2 proxies removed)
        self.assertEqual(len(cell.sections), 1)

        # Assert that the proxied locations can be found
        proxy_1 = cell.get_location((1, 0))
        proxy_2 = cell.get_location((2, 0))

        true_loc = cell.get_location((0, 1))
        # And that they refer to the correct unproxied Section location
        self.assertEqual(true_loc, proxy_1.proxied_loc)
        self.assertEqual(true_loc, proxy_2.proxied_loc)

        # Assert that the user is warned when using proxies in possibly unsafe
        # ways.
        with self.assertWarns(ProxyWarning):
            _ = proxy_1.section
        with self.assertWarns(ProxyWarning):
            _ = proxy_1.mechanisms

    def _build_single_point_root_multiple_children(self, middle_label="dendrites"):
        """
        This test asserts that when a single point branch occurs as a root
        branch, the children are connected to its first child, when all
        children are multipoint branches. This test also asserts that the
        proxy location accessor heuristic prefers same-label children.
        """
        schematic = Schematic()
        schematic.definition = define_model(
            {"cable_types": {"soma": {"mechanisms": {"pas": {}}}}}, use_defaults=True
        )

        # Morphology diagram:
        #   _
        # .
        #   _
        #   _

        # We start the morphology off by creating single-point-branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])
        # Then branch 1 with 3 points for the top of the fork
        schematic.create_location((1, 0), (0, 0, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((1, 1), (1, 1, 0), 1, ["dendrites"])
        schematic.create_location((1, 2), (2, 1, 0), 1, ["dendrites"])
        # Then branch 2 with 3 points for the higher bottom of the fork
        schematic.create_location((2, 0), (0, 0, 0), 1, [middle_label], endpoint=(0, 0))
        schematic.create_location((2, 1), (1, -1, 0), 1, [middle_label])
        schematic.create_location((2, 2), (2, -1, 0), 1, [middle_label])
        # Finally, branch 3 with 3 points for the lower bottom of the fork
        schematic.create_location((3, 0), (0, 0, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((3, 1), (1, -2, 0), 1, ["dendrites"])
        schematic.create_location((3, 2), (2, -2, 0), 1, ["dendrites"])

        return neuron_build(schematic)

    def test_single_point_root_multiple_children(self):
        cell = self._build_single_point_root_multiple_children()
        # Assert that the single point branch did not create a section.
        self.assertEqual(len(cell.sections), 3)

        # Assert that the 3 sibling branches have been connected to the first sibling.
        self.assertEqual(
            cell.sections[0]._references, [cell.sections[1], cell.sections[2]]
        )
        self.assertEqual(cell.sections[1]._references, [cell.sections[0]])
        self.assertEqual(cell.sections[2]._references, [cell.sections[0]])

    def test_double_single_point(self):
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        # - . . -

        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])
        schematic.create_location((0, 1), (1, 0, 0), 1, ["soma"])
        schematic.create_location((1, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(0, 1))
        schematic.create_location((2, 0), (2, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((3, 0), (3, 0, 0), 1, ["dendrites"], endpoint=(2, 0))
        schematic.create_location((3, 1), (4, 0, 0), 1, ["dendrites"])

        cell = neuron_build(schematic)

        self.assertEqual(len(cell.sections), 2)
        self.assertEqual(cell.sections[0]._references, [cell.sections[1]])
        self.assertEqual(cell.sections[1]._references, [cell.sections[0]])

    def _build_single_point_with_parent_and_multiple_children(
        self, parent_label="dendrites", middle_label="dendrites"
    ):
        """
        This test verifies that we connect a proxy with a parent to the parent
        electrically and hand the user a location accessor to the parent.
        """
        schematic = Schematic()
        schematic.definition = define_model(
            {
                "cable_types": {
                    "soma": {"mechanisms": {"pas": {}, "hh": {}}},
                    "dendrites": {"mechanisms": {"pas": {}}},
                }
            },
            use_defaults=True,
        )

        # Morphology diagram:
        #     _
        # - .
        #     _
        #     _

        # We start the morphology off by creating branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, [parent_label])
        schematic.create_location((0, 1), (1, 0, 0), 1, [parent_label])
        # Then branch 1 as a single point branch connected to branch 0
        schematic.create_location((1, 0), (1, 0, 0), 1, ["soma"], endpoint=(0, 1))
        # Then 3 sibling branches connected to single-point-branch 1
        schematic.create_location((2, 0), (1, 0, 0), 1, [middle_label], endpoint=(1, 0))
        schematic.create_location((2, 1), (2, 1, 0), 1, [middle_label])
        schematic.create_location((3, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((3, 1), (2, 0, 0), 1, ["dendrites"])
        schematic.create_location((4, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((4, 1), (2, -1, 0), 1, ["dendrites"])

        return neuron_build(schematic)

    def test_single_point_with_parent_and_multiple_children(self):
        cell = self._build_single_point_with_parent_and_multiple_children()
        # Assert that the single point branch did not create a section.
        self.assertEqual(len(cell.sections), 4)

        # Assert that the 3 sibling branches have been connected to branch 0.
        self.assertEqual(
            cell.sections[0]._references,
            [cell.sections[1], cell.sections[2], cell.sections[3]],
        )
        self.assertEqual(cell.sections[1]._references, [cell.sections[0]])
        self.assertEqual(cell.sections[2]._references, [cell.sections[0]])
        self.assertEqual(cell.sections[3]._references, [cell.sections[0]])

    def test_complex_single_point_chain(self):
        """
        This test verifies that even when multiple single point branches occur
        as children of each other in a complex branched morphology, they are
        eliminated correctly.
        """
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        #   . -
        # .   . -
        #       -
        #
        #     .
        #   - . -
        #       . -

        schematic.create_location((0, 0), (1, 0, 0), 1, ["soma"])
        schematic.create_location((1, 0), (0, 1, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((2, 0), (0, 2, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((2, 1), (0, 3, 0), 1, ["dendrites"])
        schematic.create_location((3, 0), (1, 2, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((4, 0), (1, 3, 0), 1, ["dendrites"], endpoint=(3, 0))
        schematic.create_location((4, 1), (1, 4, 0), 1, ["dendrites"])
        schematic.create_location((5, 0), (2, 3, 0), 1, ["dendrites"], endpoint=(3, 0))
        schematic.create_location((5, 1), (2, 4, 0), 1, ["dendrites"])
        schematic.create_location((6, 0), (5, 1, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((6, 1), (5, 2, 0), 1, ["dendrites"])
        schematic.create_location((7, 0), (4, 2, 0), 1, ["dendrites"], endpoint=(6, 1))
        schematic.create_location((8, 0), (5, 2, 0), 1, ["dendrites"], endpoint=(6, 1))
        schematic.create_location((9, 0), (5, 3, 0), 1, ["dendrites"], endpoint=(8, 0))
        schematic.create_location((9, 1), (5, 4, 0), 1, ["dendrites"])
        schematic.create_location((10, 0), (6, 3, 0), 1, ["dendrites"], endpoint=(8, 0))
        schematic.create_location((11, 0), (6, 4, 0), 1, ["dendrites"], endpoint=(10, 0))
        schematic.create_location((11, 1), (6, 5, 0), 1, ["dendrites"])

        cell = neuron_build(schematic)
        # There are 6 branches
        self.assertEqual(6, len(cell.sections))

        # From the diagram, collapsing the root proxy should connect 4
        # siblings together:
        #  * the 3 terminal branches from the top part of the diagram
        #  * the root-most branch from the bottom part of the diagram
        self.assertEqual(
            cell.sections[0]._references,
            [cell.sections[1], cell.sections[2], cell.sections[3]],
        )
        self.assertEqual(cell.sections[1]._references, [cell.sections[0]])
        self.assertEqual(cell.sections[2]._references, [cell.sections[0]])

        # Collapsing the proxies in the lower part of the diagram shows that
        # the 2 terminal branches should be connected to the root-most branch.
        self.assertEqual(
            cell.sections[3]._references,
            # The root-most branch is connected to the first branch (
            # top-diagram) and to the 2 terminal branches (bottom-diagram).
            [cell.sections[0], cell.sections[4], cell.sections[5]],
        )
        # The 2 terminal branches (bottom-diagram) are connected to the
        # root-most branch.
        self.assertEqual(cell.sections[4]._references, [cell.sections[3]])
        self.assertEqual(cell.sections[5]._references, [cell.sections[3]])

    def test_location_accessor_heuristic_parent_same_label(self):
        """
        Assert that the location accessor points to the parent with the
        same labels as the proxy, which users that don't know about proxies
        likely intend to do.
        """
        # Assert that parent is proxied when children share no label
        cell = self._build_single_point_with_parent_and_multiple_children(
            parent_label="soma", middle_label="dendrites"
        )
        proxy_loc = cell.get_location((1, 0))
        self.assertEqual((0, 1), proxy_loc._proxied_loc.location)
        # Assert that parent is proxied even when children also have same label
        cell = self._build_single_point_with_parent_and_multiple_children(
            parent_label="soma", middle_label="soma"
        )
        proxy_loc = cell.get_location((1, 0))
        self.assertEqual((0, 1), proxy_loc._proxied_loc.location)

        # Assert that we're warning the user about proxy ambiguity
        with self.assertWarns(ProxyWarning):
            section = proxy_loc.section
        with self.assertWarns(ProxyWarning):
            mechanisms = proxy_loc.mechanisms

        # Assert that the correct section is proxied
        self.assertEqual(cell.get_location((0, 1)).section, section)
        # Assert that the correct mechanisms are proxied
        self.assertEqual(cell.get_location((0, 1)).section, mechanisms["pas"]._section)

    def test_location_accessor_heuristic_child_same_label(self):
        """
        Assert that even though the branches have electrically been connected to
        the parent, the location accessor points to the child with the
        same labels as the proxy, which users that don't know about proxies
        likely intend to do.
        """
        cell = self._build_single_point_root_multiple_children(middle_label="soma")
        proxy_loc = cell.get_location((0, 0))

        # Assert that we're warning the user about proxy ambiguity
        with self.assertWarns(ProxyWarning):
            section = proxy_loc.section
        with self.assertWarns(ProxyWarning):
            mechanisms = proxy_loc.mechanisms

        # Assert that the section matches
        print(cell.get_location((2, 0)).section, section)
        self.assertEqual(cell.get_location((2, 0)).section, section)
        # Assert that we can access its mechanisms
        self.assertEqual(section, mechanisms["pas"]._section)
        # And that it explains to users why it might not contain the mechanisms
        # they expected
        with self.assertRaisesRegex(
            KeyError,
            r"'foo' \- Location \(0, 0\)\[soma\] proxies \(2, 0\)\[soma\]\. Mechanism 'foo' not found on proxied location\.",
        ):
            _foo = mechanisms["foo"]

    def test_location_accessor_heuristic_parent_diff_label(self):
        """
        Assert that the location accessor points to the parent when no branch
        has the same labels as the proxy
        """
        # Assert that parent is proxied when children share no label
        cell = self._build_single_point_with_parent_and_multiple_children(
            parent_label="dendrites", middle_label="dendrites"
        )
        proxy_loc = cell.get_location((1, 0))
        self.assertEqual((0, 1), proxy_loc._proxied_loc.location)

        # Assert that we're warning the user about proxy ambiguity
        with self.assertWarns(ProxyWarning):
            section = proxy_loc.section
        with self.assertWarns(ProxyWarning):
            mechanisms = proxy_loc.mechanisms

        # Assert that the correct section is proxied
        self.assertEqual(cell.get_location((0, 1)).section, section)
        # Assert that the correct mechanisms are proxied
        self.assertEqual(cell.get_location((0, 1)).section, mechanisms["pas"]._section)
        # And that it explains to users why it might not contain the mechanisms
        # they expected
        with self.assertRaisesRegex(
            KeyError,
            r"'hh' \- Location \(1, 0\)\[soma\] proxies \(0, 1\)\[dendrites\]\. Mechanism 'hh' not found on proxied location\.",
        ):
            _hh = mechanisms["hh"]

    def test_location_accessor_heuristic_no_parent_diff_label(self):
        """
        Assert that the location accessor points to the first child when no
        branch has the same labels as the proxy, in the absence of a parent
        """
        cell = self._build_single_point_root_multiple_children(middle_label="dendrites")
        proxy_loc = cell.get_location((0, 0))

        # Assert that we're warning the user about proxy ambiguity
        with self.assertWarns(ProxyWarning):
            section = proxy_loc.section
        with self.assertWarns(ProxyWarning):
            _mechanisms = proxy_loc.mechanisms

        # Assert that the section matches the first child
        self.assertEqual(cell.get_location((1, 0)).section, section)
