import unittest
import warnings

import numpy as np
from neo import Block

from bsb import decode_annotation, encode_annotation
from bsb.simulation.results import read_simulation_config


class TestAnnotationCodec(unittest.TestCase):
    """Structured metadata has to survive a write, and degrade rather than raise."""

    def test_a_nested_bundle_round_trips(self):
        bundle = {"duration": 100, "devices": {"pg": {"rate": 1600.0, "on": True}}}
        self.assertEqual(bundle, decode_annotation(encode_annotation(bundle)))

    def test_numpy_values_are_encodable(self):
        bundle = {"array": np.arange(3), "scalar": np.float64(2.5)}
        decoded = decode_annotation(encode_annotation(bundle))
        self.assertEqual([0, 1, 2], decoded["array"])
        self.assertEqual(2.5, decoded["scalar"])

    def test_an_unencodable_value_degrades_instead_of_raising(self):
        # Losing the metadata is a smaller loss than losing what it describes, so a
        # value that cannot be encoded must not take the run down with it.
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            encoded = encode_annotation({"bad": object()}, "test metadata")
        self.assertEqual("null", encoded)
        self.assertTrue(any("test metadata" in str(w.message) for w in caught))

    def test_decoding_passes_through_what_was_never_encoded(self):
        self.assertEqual(["a", "b"], decode_annotation(["a", "b"]))
        self.assertEqual(7, decode_annotation(7))

    def test_decoding_a_non_json_string_returns_the_string(self):
        self.assertEqual("not json", decode_annotation("not json"))

    def test_decoding_nothing_returns_the_default(self):
        self.assertIsNone(decode_annotation(None))
        self.assertEqual({}, decode_annotation(None, default={}))


class TestSimulationConfigAnnotation(unittest.TestCase):
    """The configuration stored beside a set of results."""

    def test_a_stored_configuration_reads_back(self):
        tree = {"duration": 100, "devices": {"pg": {"rate": 1600}}}
        block = Block(name="sim", config=encode_annotation(tree))
        self.assertEqual(tree, read_simulation_config(block))

    def test_a_block_without_a_configuration_reads_as_none(self):
        self.assertIsNone(read_simulation_config(Block(name="sim")))

    def test_a_legacy_gutted_configuration_warns_rather_than_raising(self):
        # Before the configuration was encoded, `NixIO` wrote a dict annotation as
        # nothing but its top-level keys. Those files still exist; their values were
        # never written and cannot be recovered, so reading says so and returns what
        # is there rather than refusing the file.
        block = Block(name="sim", config=["duration", "devices"])
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            recovered = read_simulation_config(block)
        self.assertEqual(["duration", "devices"], recovered)
        self.assertTrue(any("top-level keys" in str(w.message) for w in caught))


if __name__ == "__main__":
    unittest.main()
