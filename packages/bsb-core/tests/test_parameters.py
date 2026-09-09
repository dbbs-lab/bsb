import unittest

import numpy as np
from bsb_test import FixedPosConfigFixture, NumpyTestCase, RandomStorageFixture

from bsb import (
    CellParameter,
    ConnectionParameter,
    Constant,
    DistanceDelayParameter,
    Parameter,
    PointParameter,
    Scaffold,
    constant_parameter,
    parameters_of_type,
)
from bsb.config import Configuration


class TestParameterArities(unittest.TestCase):
    """Each arity is its own dynamic root, so a strategy resolves within its arity."""

    def test_each_arity_is_its_own_root(self):
        for cls in (CellParameter, PointParameter, ConnectionParameter):
            with self.subTest(arity=cls.__name__):
                self.assertIs(
                    cls,
                    cls._config_dynamic_root,
                    "arity must be castable in its own right",
                )

    def test_arities_do_not_share_a_classmap(self):
        maps = [
            id(cls._config_dynamic_classmap)
            for cls in (CellParameter, PointParameter, ConnectionParameter)
        ]
        self.assertEqual(len(maps), len(set(maps)), "arities share a classmap")

    def test_distance_delay_registers_on_connections_only(self):
        self.assertIn("distance_delay", ConnectionParameter._config_dynamic_classmap)
        self.assertNotIn("distance_delay", CellParameter._config_dynamic_classmap)

    def test_constant_is_a_parameter_but_in_no_classmap(self):
        self.assertTrue(issubclass(Constant, Parameter))
        for cls in (CellParameter, PointParameter, ConnectionParameter):
            with self.subTest(arity=cls.__name__):
                self.assertNotIn(Constant, cls._config_dynamic_classmap.values())


class TestParameterCasting(unittest.TestCase):
    """The shorthands a value may be written in, and what they cast to."""

    def setUp(self):
        self.wide = parameters_of_type(CellParameter)
        self.narrow = constant_parameter()

    def test_scalar_casts_to_constant_parameter(self):
        param = self.wide(250.0)
        self.assertIsInstance(param, Constant)
        self.assertEqual(250.0, param.compute())

    def test_list_and_string_cast_to_constant_parameter(self):
        self.assertEqual([1, 2, 3], self.wide([1, 2, 3]).compute())
        self.assertEqual("uniform", self.wide("uniform").compute())

    def test_strategy_casts_to_the_arity(self):
        param = parameters_of_type(ConnectionParameter)(
            {"strategy": "distance_delay", "axon_speed": 2.0}
        )
        self.assertIsInstance(param, DistanceDelayParameter)

    def test_an_existing_parameter_passes_through(self):
        param = self.wide(5)
        self.assertIs(param, self.wide(param))

    def test_constants_refuse_a_computed_parameter(self):
        with self.assertRaises(TypeError) as ctx:
            self.narrow({"strategy": "distance_delay", "axon_speed": 2.0}, _key="delay")
        self.assertIn("parameters", str(ctx.exception))

    def test_a_constant_inverts_back_to_a_bare_value(self):
        # A constant was written as a bare value, so the config it serialises back to
        # must be that bare value and not a node the user never wrote.
        self.assertEqual(250.0, self.wide.__inv__(self.wide(250.0)))

    def test_the_example_shown_is_the_shorthand(self):
        # The config reference builds its examples by asking a handler what a value of
        # its type looks like. Without an answer it casts a stand-in instead and shows
        # a parameter node, which is both the wrong notation to teach and unwritable
        # to json.
        for handler in (self.wide, self.narrow):
            with self.subTest(handler=type(handler).__name__):
                self.assertEqual(1.0, handler.__hint__())


class TestDistanceDelay(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    """The one computed strategy that ships, against a real network."""

    def setUp(self):
        super().setUp()
        self.cfg.connectivity.add(
            "all_to_all",
            dict(
                strategy="bsb.connectivity.AllToAll",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["test_cell"]),
            ),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile()

    def test_delay_is_distance_over_speed(self):
        cs = self.network.get_connectivity_set("all_to_all")
        pre_locs, post_locs = cs.load_connections().all()
        param = parameters_of_type(ConnectionParameter)(
            {"strategy": "distance_delay", "axon_speed": 2.0}
        )
        simulation = type("_Sim", (), {"resolution": 1e-9})()

        delays = param.compute(simulation, cs, pre_locs, post_locs)

        positions = self.network.get_placement_set("test_cell").load_positions()
        expected = (
            np.linalg.norm(
                positions[pre_locs[:, 0]] - positions[post_locs[:, 0]], axis=-1
            )
            / 2.0
        )
        self.assertClose(expected, delays)

    def test_delay_never_undercuts_the_resolution(self):
        cs = self.network.get_connectivity_set("all_to_all")
        pre_locs, post_locs = cs.load_connections().all()
        param = parameters_of_type(ConnectionParameter)(
            {"strategy": "distance_delay", "axon_speed": 1e12}
        )
        simulation = type("_Sim", (), {"resolution": 0.1})()

        delays = param.compute(simulation, cs, pre_locs, post_locs)

        # An implausibly fast axon would otherwise deliver faster than a time step.
        self.assertTrue(np.all(delays >= 0.1))


class TestDelayReachesItsSimulation(
    RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """
    Flooring a delay at a time step is this parameter's requirement, not the
    framework's, so it asks the simulation it is configured on for one.

    How deep it sits is the backend's business: a parameter in a model's
    ``parameters`` is a different depth from one written on a synapse node, so the
    simulation is found by what it is rather than by counting parents.
    """

    def network(self, **sim):
        cfg = Configuration.default(
            cell_types={"c": {"spatial": {"radius": 1, "count": 2}}},
            partitions={"l": {"thickness": 10}},
            placement={
                "p": {
                    "strategy": "bsb.placement.RandomPlacement",
                    "cell_types": ["c"],
                    "partitions": ["l"],
                }
            },
            connectivity={
                "cc": {
                    "strategy": "bsb.connectivity.AllToAll",
                    "presynaptic": {"cell_types": ["c"]},
                    "postsynaptic": {"cell_types": ["c"]},
                }
            },
            simulations={
                "s": {
                    "simulator": "arbor",
                    "duration": 10,
                    "cell_models": {},
                    "devices": {},
                    "connection_models": {
                        "cc": {
                            "weight": 1.0,
                            "delay": 1.0,
                            "parameters": {
                                "delay": {
                                    "strategy": "distance_delay",
                                    "axon_speed": 2.0,
                                }
                            },
                        }
                    },
                    **sim,
                }
            },
        )
        return Scaffold(cfg, self.storage)

    def test_it_finds_the_simulation_it_is_configured_on(self):
        network = self.network(resolution=0.25)
        param = network.simulations.s.connection_models.cc.parameters.delay
        self.assertIs(param.simulation, network.simulations.s)
        self.assertEqual(0.25, param.simulation.resolution)


if __name__ == "__main__":
    unittest.main()
