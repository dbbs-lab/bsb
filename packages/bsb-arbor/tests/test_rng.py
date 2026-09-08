import unittest

from bsb import MPI, Scaffold
from bsb.config import Configuration
from bsb_test import RandomStorageFixture


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestPoissonSeeding(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    """
    Arbor seeds each generator itself, so it is handed a number per cell.

    Seeded with the gid alone every run drew the same spike train, whatever the network
    said, which is neither reproducible on purpose nor a replicate.
    """

    def network(self, rng):
        cfg = Configuration.default(
            rng=rng,
            cell_types={"cell": {"spatial": {"radius": 1, "count": 2}}},
            partitions={"layer": {"thickness": 10}},
            placement={
                "p": {
                    "strategy": "bsb.placement.RandomPlacement",
                    "cell_types": ["cell"],
                    "partitions": ["layer"],
                }
            },
            simulations={
                "sim": {
                    "simulator": "arbor",
                    "duration": 10,
                    "resolution": 0.1,
                    "cell_models": {},
                    "connection_models": {},
                    "devices": {
                        "noise": {
                            "device": "poisson_generator",
                            "rate": 10.0,
                            "weight": 1.0,
                            "delay": 1.0,
                            "targetting": {"strategy": "all"},
                        }
                    },
                }
            },
        )
        return Scaffold(cfg, self.storage)

    def seeds(self, rng, gids=(0, 1, 2, 3)):
        device = self.network(rng).simulations.sim.devices.noise
        return [
            device.random_generator.derive(("poisson", device.name, gid)) for gid in gids
        ]

    def test_a_pinned_root_gives_the_same_spike_trains(self):
        self.assertEqual(
            self.seeds({"seed": 42}),
            self.seeds({"seed": 42}),
            "one seed has to reproduce the run it seeded",
        )

    def test_another_root_gives_other_spike_trains(self):
        self.assertNotEqual(
            self.seeds({"seed": 42}),
            self.seeds({"seed": 43}),
            "the root seed has to reach the generators, or a run is not a replicate",
        )

    def test_every_cell_draws_its_own(self):
        drawn = self.seeds({"seed": 42})
        self.assertEqual(len(drawn), len(set(drawn)), "one seed per cell, not one seed")
