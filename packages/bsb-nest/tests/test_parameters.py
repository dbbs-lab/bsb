import unittest
from types import SimpleNamespace

import numpy as np
from bsb import ConfigurationError, Constant

from bsb_nest._parameters import merged
from bsb_nest.cell import NestCell
from bsb_nest.connection import NestConnection


class TestMergingNotations(unittest.TestCase):
    """
    A model writes its parameters apart for the reader and means one thing by them.

    Everything downstream deals with one mapping, so the notations have to come back
    together with no seam and no notation quietly winning over another.
    """

    def test_notations_come_back_as_one_mapping(self):
        collected = merged("a model", {"C_m": Constant(250.0)}, {"V_th": Constant(-55.0)})
        self.assertEqual({"C_m", "V_th"}, set(collected))
        self.assertEqual(250.0, collected["C_m"].compute())
        self.assertEqual(-55.0, collected["V_th"].compute())

    def test_naming_a_parameter_twice_is_an_error(self):
        with self.assertRaises(ConfigurationError) as ctx:
            merged("a model", {"C_m": Constant(250.0)}, {"C_m": Constant(300.0)})
        self.assertIn("C_m", str(ctx.exception))
        self.assertIn("a model", str(ctx.exception))

    def test_the_order_written_is_the_order_merged(self):
        collected = merged("a model", {"a": Constant(1)}, {"b": Constant(2)})
        self.assertEqual(["a", "b"], list(collected))

    def test_merging_nothing_is_empty_rather_than_an_error(self):
        self.assertEqual({}, merged("a model"))
        self.assertEqual({}, merged("a model", {}, {}))


class TestSelectingPerPair(unittest.TestCase):
    """
    Several connections may join one pair of cells, and NEST is asked for one
    connection per pair, so a per-connection answer is read down to a per-pair one.
    A single value is already every pair's, and has nothing to read down.
    """

    def _connection(self, **synapse):
        conn = NestConnection(
            name="a_to_b", synapses=[{"model": "static_synapse", **synapse}]
        )
        # `get_syn_specs` hands a parameter the simulation it belongs to, which is
        # two nodes up; nothing here computes over it.
        conn._config_parent = SimpleNamespace(_config_parent=None)
        return conn

    def _specs(self, conn, n_conn, take):
        locs = np.zeros((n_conn, 3), dtype=int)
        return conn.get_syn_specs(cs=object(), pre_locs=locs, post_locs=locs, take=take)

    def test_one_value_stands_for_every_pair(self):
        conn = self._connection(weight=3.0, delay=1.0)
        spec = self._specs(conn, 4, np.array([0, 2]))[0]
        self.assertEqual(3.0, spec["weight"])
        self.assertEqual(1.0, spec["delay"])

    def test_a_value_per_connection_is_read_down_to_the_pair(self):
        conn = self._connection(weight=[1.0, 2.0, 3.0, 4.0], delay=1.0)
        spec = self._specs(conn, 4, np.array([0, 2]))[0]
        self.assertEqual([1.0, 3.0], list(spec["weight"]))


class TestWritingParametersBackOut(unittest.TestCase):
    """
    A run records its own configuration, and has to be able to read it back.

    NEST spells constants in both notations the framework offers, one per key and
    one caught, so both have to hand a bare value back as a bare value.
    """

    def test_a_cell_model_writes_bare_values_back(self):
        cell = NestCell(
            name="top",
            model="iaf_psc_alpha",
            constants={"t_ref": 1.5},
            parameters={"V_m": -62.0},
        )
        tree = cell.__tree__()
        self.assertEqual({"t_ref": 1.5}, tree["constants"])
        self.assertEqual({"V_m": -62.0}, tree["parameters"])

    def test_a_synapse_writes_a_caught_constant_back(self):
        conn = NestConnection(
            name="a_to_b",
            synapses=[{"model": "static_synapse", "weight": 3.0, "tau_psc": 2.0}],
        )
        # `tau_psc` is not a declared attribute, so the catch-all is what took it.
        self.assertEqual(2.0, conn.__tree__()["synapses"][0]["tau_psc"])
