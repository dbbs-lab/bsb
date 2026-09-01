import unittest

from bsb_test import RandomStorageFixture

from bsb import Scaffold
from bsb.config import Configuration


class _NetworkMixin:
    """Builds networks whose only interesting configuration is their randomness."""

    def network(self, rng=None):
        kwargs = {}
        if rng is not None:
            kwargs["rng"] = rng
        return Scaffold(Configuration.default(**kwargs), self.random_storage())


class TestReplicateAndReproduce(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """The two modes the whole design exists to provide."""

    def draw(self, network):
        return network.configuration.rng.get_rng(
            key=("place", (0, 0, 0), "cell")
        ).random()

    def test_an_unseeded_config_is_a_new_replicate_every_run(self):
        seeds = {self.network().configuration.rng.seed for _ in range(3)}
        self.assertEqual(3, len(seeds), "an unseeded run must not repeat itself")

    def test_every_run_records_the_seed_it_used(self):
        network = self.network()
        stored = network.configuration.__tree__()["rng"]
        self.assertEqual(
            network.configuration.rng.seed,
            stored["seed"],
            "a drawn seed must reach the stored configuration, or the run is lost",
        )

    def test_feeding_a_recorded_config_back_reproduces_the_run(self):
        first = self.network()
        recorded = first.configuration.__tree__()["rng"]

        self.assertEqual(self.draw(first), self.draw(self.network(recorded)))

    def test_a_pinned_seed_is_left_alone(self):
        network = self.network({"seed": 1234})
        self.assertEqual(1234, network.configuration.rng.seed)
        self.assertEqual(1234, network.configuration.__tree__()["rng"]["seed"])


class TestDerivation(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """Streams are derived from what is being drawn for, never from the rank."""

    def setUp(self):
        super().setUp()
        self.rng = self.network({"seed": 42}).configuration.rng

    def test_the_same_key_gives_the_same_stream(self):
        self.assertEqual(
            self.rng.get_rng(key=("place", (0, 0, 0))).random(),
            self.rng.get_rng(key=("place", (0, 0, 0))).random(),
        )

    def test_different_keys_give_different_streams(self):
        draws = {
            self.rng.get_rng(key=key).random()
            for key in (
                ("place", (0, 0, 0), "cell_a"),
                ("place", (1, 0, 0), "cell_a"),
                ("place", (0, 0, 0), "cell_b"),
                ("connect", (0, 0, 0), "cell_a"),
            )
        }
        self.assertEqual(4, len(draws), "each thing drawn for gets its own stream")

    def test_a_string_key_is_stable_across_processes(self):
        # Python's own `hash` is salted per process; a salted key would reseed on
        # every invocation and silently destroy reproducibility.
        import subprocess
        import sys

        script = (
            "from bsb.rng import _stable_ints; print(_stable_ints(('place', 'cell_a')))"
        )
        runs = {
            subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True
            ).stdout.strip()
            for _ in range(2)
        }
        self.assertEqual(1, len(runs), f"key hashing is not stable: {runs}")

    def test_providers_derive_from_the_root_seed(self):
        rng = self.network({"seed": 7, "providers": {"placement": {}}}).configuration.rng
        provider = rng.providers["placement"]
        self.assertIsNotNone(provider.seed, "an unpinned provider derives a seed")
        self.assertNotEqual(7, provider.seed, "and it is not just the root seed")

    def test_a_pinned_provider_holds_while_the_rest_varies(self):
        # The workflow this exists for: same network, different simulation noise.
        pinned = {"providers": {"placement": {"seed": 99}}}
        first, second = self.network(pinned), self.network(pinned)

        self.assertEqual(
            first.configuration.rng.get_rng("placement", ("chunk",)).random(),
            second.configuration.rng.get_rng("placement", ("chunk",)).random(),
            "a pinned provider must not move between runs",
        )
        self.assertNotEqual(
            first.configuration.rng.seed,
            second.configuration.rng.seed,
            "while the root seed still varies",
        )


class TestAccessor(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """Reaching randomness from a node booted into a network."""

    def test_a_node_draws_from_its_network(self):
        from bsb.rng import get_rng

        network = self.network({"seed": 5})
        self.assertEqual(
            get_rng(network, key=("x",)).random(),
            network.configuration.rng.get_rng(key=("x",)).random(),
        )

    def test_an_unattached_object_says_so(self):
        from bsb import ConfigurationError
        from bsb.rng import get_rng

        with self.assertRaises(ConfigurationError):
            get_rng(object())


if __name__ == "__main__":
    unittest.main()
