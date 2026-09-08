import unittest

from bsb import ConfigurationError, Constant

from bsb_nest._parameters import merged


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
