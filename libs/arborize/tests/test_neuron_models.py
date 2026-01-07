import os
import unittest

from arborize import Schematic, define_model, neuron_build
from arborize.exceptions import (
    UnconnectedPointInSpaceWarning,
    UnknownLocationError,
    UnknownSynapseError,
)
from patch import p

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
        branches, that they are discarded.
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

        self.assertEqual(len(cell.sections), 1)

    def test_single_point_root_multiple_children(self):
        """
        This test asserts that when a single point branch occurs as a root
        branch, the children are connected to its first child, when all
        children are multipoint branches.
        """
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

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
        schematic.create_location((2, 0), (0, 0, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((2, 1), (1, -1, 0), 1, ["dendrites"])
        schematic.create_location((2, 2), (2, -1, 0), 1, ["dendrites"])
        # Finally, branch 3 with 3 points for the lower bottom of the fork
        schematic.create_location((3, 0), (0, 0, 0), 1, ["dendrites"], endpoint=(0, 0))
        schematic.create_location((3, 1), (1, -2, 0), 1, ["dendrites"])
        schematic.create_location((3, 2), (2, -2, 0), 1, ["dendrites"])

        cell = neuron_build(schematic)

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

    def test_single_point_with_parent_and_multiple_children(self):
        schematic = Schematic()
        schematic.definition = define_model({}, use_defaults=True)

        # Morphology diagram:
        #     _
        # - .
        #     _
        #     _

        # We start the morphology off by creating branch 0 at 0, 0, 0
        schematic.create_location((0, 0), (0, 0, 0), 1, ["soma"])
        schematic.create_location((0, 1), (1, 0, 0), 1, ["soma"])
        # Then branch 1 as a single point branch connected to branch 0
        schematic.create_location((1, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(0, 1))
        # Then 3 sibling branches connected to single-point-branch 1
        schematic.create_location((2, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((2, 1), (2, 1, 0), 1, ["dendrites"])
        schematic.create_location((3, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((3, 1), (2, 0, 0), 1, ["dendrites"])
        schematic.create_location((4, 0), (1, 0, 0), 1, ["dendrites"], endpoint=(1, 0))
        schematic.create_location((4, 1), (2, -1, 0), 1, ["dendrites"])

        cell = neuron_build(schematic)

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
