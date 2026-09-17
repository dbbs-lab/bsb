import unittest

from arborize import bsb_schematic, define_model, neuron_build
from bsb import Branch, Configuration, Morphology, SomaTargetting
from bsb_test import (
    ConfigFixture,
    NetworkFixture,
    RandomStorageFixture,
)

from bsb_neuron.cell import ArborizedModel, ArborizeModelTypeHandler
from bsb_neuron.connection import SynapseSpec
from bsb_neuron.simulation import NeuronSimulation


class TestArborizedModel(
    RandomStorageFixture,
    ConfigFixture,
    NetworkFixture,
    unittest.TestCase,
    config="neuron_minimal",
    engine_name="fs",
):
    def setUp(self):
        super().setUp()
        hh_soma = {
            "cable_types": {
                "soma": {
                    "cable": {"Ra": 10, "cm": 1},
                    "mechanisms": {"pas": {"e": -70, "g": 0.01}, "hh": {}},
                }
            },
            "synapse_types": {"ExpSyn": {"parameters": {"U": 0.77}}},
        }
        self.network.cell_types.add(
            "A",
            {
                "spatial": {"count": 1},
            },
        )
        self.network.simulations["test"].cell_models = {
            "A": ArborizedModel(model=hh_soma)
        }
        self.network.compile()
        self.model = define_model(hh_soma)

    def test_typehandler_inv(self):
        # first i test directly the ArborizeModelTypeHandler __inv__ func
        self.model._cfg_inv = "model_definition"
        model_handler = ArborizeModelTypeHandler()
        reverse_model = model_handler.__inv__(self.model)
        self.assertEqual(reverse_model, "model_definition")

        # Now i check if a ModelDefinition is correctly converted
        # into a Configuration tree
        cfg_tree = self.cfg.__tree__()
        new_cfg = Configuration(cfg_tree)

        new_cell_mdl = new_cfg.simulations.test.cell_models.A.model
        self.assertEqual(
            10,
            new_cell_mdl._cable_types["soma"].cable.Ra,
            "Cell models cable types are not correctly converted to tree obj.",
        )
        self.assertEqual(
            {"e": -70, "g": 0.01},
            new_cell_mdl._cable_types["soma"].mechs["pas"].parameters,
            "Mechanisms are not correctly converted to tree obj.",
        )
        self.assertEqual(
            {"U": 0.77},
            new_cell_mdl._synapse_types["ExpSyn"].parameters,
            "Cell models synapses are not correctly converted to tree obj.",
        )


class TestSynapseSpecDefaults(unittest.TestCase):
    def test_default_delay_is_a_usable_mindelay(self):
        # The delays in a network determine NEURON's `mindelay`, and
        # `NeuronAdapter.run` always calls `pc.set_maxstep`, which rejects a `mindelay`
        # of 0 or below the fixed timestep. A default that cannot be simulated is not a
        # default, so it has to clear both bounds for the default resolution.
        delay = SynapseSpec("ExpSyn").delay
        resolution = NeuronSimulation.resolution.default
        self.assertGreater(delay, 0, "a mindelay of 0 aborts every NEURON simulation")
        self.assertGreaterEqual(
            delay,
            resolution,
            "a mindelay below the timestep aborts fixed step NEURON simulations",
        )


class TestSomaTargetting(unittest.TestCase):
    """The soma is wherever the morphology labels it, not its first point."""

    def _build(self, morphology):
        definition = define_model(
            {
                "cable_types": {
                    label: {"cable": {"Ra": 10, "cm": 1}}
                    for label in ("soma", "dendrites")
                }
            }
        )
        definition.use_defaults = True
        return neuron_build(bsb_schematic(morphology, definition))

    def test_every_location_labelled_soma(self):
        dendrite = Branch([[0, 0, 0], [0, 10, 0], [0, 20, 0]], [1, 1, 1])
        dendrite.label(["dendrites"])
        soma = Branch([[0, 0, 0], [5, 0, 0], [10, 0, 0]], [5, 5, 5])
        soma.label(["soma"])
        # The soma is the second branch, so it starts at location (1, 0).
        cell = self._build(Morphology([dendrite, soma]))

        locations = SomaTargetting().get_locations(cell)

        self.assertEqual(
            [(1, 0), (1, 1), (1, 2)], sorted(tuple(loc.location) for loc in locations)
        )

    def test_a_soma_of_a_single_point(self):
        # A single point is simulated as part of the section next to it, which is a
        # dendrite here; the location is still the soma.
        soma = Branch([[0, 0, 0]], [5])
        soma.label(["soma"])
        dendrite = Branch([[0, 0, 0], [0, 10, 0], [0, 20, 0]], [1, 1, 1])
        dendrite.label(["dendrites"])
        soma.attach_child(dendrite)
        cell = self._build(Morphology([soma]))

        locations = SomaTargetting().get_locations(cell)

        self.assertEqual([(0, 0)], [tuple(loc.location) for loc in locations])
