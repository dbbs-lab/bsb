import unittest

from bsb import Scaffold
from bsb.config import Configuration
from bsb_test import RandomStorageFixture

from bsb_nest import NestAdapter


def _config(rng=None, simulations=("test",)):
    """A network that places one cell, with one or more NEST simulations on it."""
    tree = {
        "name": "test",
        "storage": {"engine": "hdf5"},
        "network": {"x": 100, "y": 100, "z": 100},
        "partitions": {"B": {"type": "layer", "thickness": 1}},
        "cell_types": {"A": {"spatial": {"radius": 1, "count": 1}}},
        "placement": {
            "placement_A": {
                "strategy": "bsb.placement.strategy.FixedPositions",
                "cell_types": ["A"],
                "partitions": ["B"],
                "positions": [[1, 1, 1]],
            }
        },
        "connectivity": {},
        "simulations": {
            name: {
                "simulator": "nest",
                "duration": 10,
                "resolution": 0.1,
                "cell_models": {"A": {"model": "iaf_psc_alpha"}},
                "connection_models": {},
                "devices": {},
            }
            for name in simulations
        },
    }
    if rng is not None:
        tree["rng"] = rng
    return Configuration(tree)


class TestKernelSeeding(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    """
    NEST is handed one number and makes its own streams out of it.

    Its own default for that number is a constant, so a network that says nothing
    about randomness used to repeat the same streams on every run of every model:
    the opposite of a replicate, and nothing recorded to reproduce from either.
    """

    def seed_of(self, cfg, name="test"):
        network = Scaffold(cfg, self.random_storage())
        return NestAdapter().master_seed(network.simulations[name]), network

    def test_the_kernel_is_seeded_from_the_root(self):
        first, _ = self.seed_of(_config({"seed": 42}))
        second, _ = self.seed_of(_config({"seed": 42}))
        self.assertEqual(first, second, "one root seed has to reproduce the kernel")

    def test_another_root_seeds_the_kernel_differently(self):
        first, _ = self.seed_of(_config({"seed": 42}))
        second, _ = self.seed_of(_config({"seed": 7}))
        self.assertNotEqual(first, second, "the kernel has to move with the root")

    def test_two_simulations_do_not_share_the_kernel(self):
        cfg = _config({"seed": 42}, simulations=("one", "two"))
        network = Scaffold(cfg, self.random_storage())
        adapter = NestAdapter()
        self.assertNotEqual(
            adapter.master_seed(network.simulations["one"]),
            adapter.master_seed(network.simulations["two"]),
            "two simulations of one network must not share NEST's streams",
        )

    def test_a_named_setting_is_handed_on_as_written(self):
        cfg = _config({"seed": 42, "settings": {"kernel": {"strategy": "nest"}}})
        cfg.simulations.test.rng = "kernel"
        seed, network = self.seed_of(cfg)
        self.assertEqual(
            network.configuration.rng.settings["kernel"].seed,
            seed,
            "the number written is the number NEST is given",
        )

    def test_a_pinned_setting_holds_while_the_root_varies(self):
        pinned = {"settings": {"kernel": {"strategy": "nest", "seed": 999}}}
        seeds = set()
        for root in (42, 7):
            cfg = _config({"seed": root, **pinned})
            cfg.simulations.test.rng = "kernel"
            seeds.add(self.seed_of(cfg)[0])
        self.assertEqual({999}, seeds, "a pinned kernel seed must not move")

    def test_an_unpinned_setting_is_written_back(self):
        cfg = _config({"seed": 42, "settings": {"kernel": {"strategy": "nest"}}})
        cfg.simulations.test.rng = "kernel"
        _, network = self.seed_of(cfg)
        stored = network.configuration.__tree__()["rng"]["settings"]["kernel"]
        self.assertIn("seed", stored, "a derived seed has to reach the stored config")

    def test_the_kernel_never_gets_a_seed_nest_refuses(self):
        # NEST rejects zero, and a derived seed is any 32 bit value.
        for root in range(1, 40):
            with self.subTest(root=root):
                self.assertGreater(self.seed_of(_config({"seed": root}))[0], 0)
