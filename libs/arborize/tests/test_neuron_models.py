import os
import unittest

from patch import p

from arborize import define_model, neuron_build
from arborize.exceptions import UnknownLocationError, UnknownSynapseError

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
        cell.insert_receiver(1, "ExpSyn", (0, 0))
        synapse = cell.get_location((0, 0)).section.synapses[0]
        self.assertEqual(synapse.gid, 1, "GId should be 1")
        synapse.stimulate(start=0, number=3, interval=10)
        r = cell.sections[0].record()
        p.run(100)
        self.assertFalse(min(r) == max(r), "No synaptic currents detected")
        cell2 = neuron_build(self.p75_expsyn)
        cell2.insert_receiver(1, "ExpSyn", (0, 0), source="i")
        synapse2 = cell2.get_location((0, 0)).section.synapses[0]
        self.assertEqual(
            synapse2._pp._interpreter.parallel._transfer_max,
            1,
            "transfer_max should be 1",
        )

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
