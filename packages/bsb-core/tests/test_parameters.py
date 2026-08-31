import unittest

import numpy as np
from bsb_test import FixedPosConfigFixture, NumpyTestCase, RandomStorageFixture

from bsb import (
    CellParameter,
    ConfigurationError,
    ConnectionParameter,
    Constant,
    DistanceDelayParameter,
    Parameter,
    ParameterizedModel,
    PointParameter,
    Scaffold,
    config,
    constant,
    parameter,
)


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
        self.wide = parameter(CellParameter)
        self.narrow = constant()

    def test_scalar_casts_to_constant(self):
        param = self.wide(250.0)
        self.assertIsInstance(param, Constant)
        self.assertTrue(param.is_constant)
        self.assertEqual(250.0, param.compute())

    def test_list_and_string_cast_to_constant(self):
        self.assertEqual([1, 2, 3], self.wide([1, 2, 3]).compute())
        self.assertEqual("uniform", self.wide("uniform").compute())

    def test_strategy_casts_to_the_arity(self):
        param = parameter(ConnectionParameter)(
            {"strategy": "distance_delay", "axon_speed": 2.0}
        )
        self.assertIsInstance(param, DistanceDelayParameter)
        self.assertFalse(param.is_constant)

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


@config.node
class _Model(ParameterizedModel):
    constants = config.dict(type=constant())
    parameters = config.dict(type=parameter(CellParameter))

    def get_parameter_groups(self):
        return (self.constants, self.parameters)

    def __str__(self):
        return "test model"


class TestParameterCollection(unittest.TestCase):
    """Every notation is collected into one mapping."""

    def test_notations_are_collected_together(self):
        model = _Model(constants={"C_m": 250.0}, parameters={"V_th": -55.0})
        collected = model.get_parameters()
        self.assertEqual({"C_m", "V_th"}, set(collected))
        self.assertEqual(250.0, collected["C_m"].compute())
        self.assertEqual(-55.0, collected["V_th"].compute())

    def test_naming_a_parameter_twice_is_an_error(self):
        model = _Model(constants={"C_m": 250.0}, parameters={"C_m": 300.0})
        with self.assertRaises(ConfigurationError) as ctx:
            model.get_parameters()
        self.assertIn("C_m", str(ctx.exception))

    def test_collecting_nothing_is_empty_rather_than_an_error(self):
        self.assertEqual({}, _Model().get_parameters())


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
        param = parameter(ConnectionParameter)(
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
        param = parameter(ConnectionParameter)(
            {"strategy": "distance_delay", "axon_speed": 1e12}
        )
        simulation = type("_Sim", (), {"resolution": 0.1})()

        delays = param.compute(simulation, cs, pre_locs, post_locs)

        # An implausibly fast axon would otherwise deliver faster than a time step.
        self.assertTrue(np.all(delays >= 0.1))


if __name__ == "__main__":
    unittest.main()
