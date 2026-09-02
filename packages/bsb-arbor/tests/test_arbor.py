import unittest

from bsb import MPI, Configuration, Scaffold
from bsb.simulation.results import read_provenance
from bsb_test import RandomStorageFixture, get_test_config_tree


@unittest.skipIf(MPI.get_size() > 1, "Skipped during parallel testing.")
class TestArbor(RandomStorageFixture, unittest.TestCase, engine_name="hdf5"):
    def test_brunel(self):
        cfg = get_test_config_tree("brunel_wbsb")
        # Remove unused nest simulation
        # This way we do not have to install nest
        del cfg["simulations"]["test_nest"]
        cfg = Configuration(cfg)
        simcfg = cfg.simulations.test_arbor

        network = Scaffold(cfg, self.storage)
        network.compile()
        result = network.run_simulation("test_arbor")

        spiketrains = result.block.segments[0].spiketrains
        # A recorder emits one train per cell it observed, so a device's spikes are
        # gathered, and how many cells it watched comes from its recorded targets.
        targets = read_provenance(result.block)["devices"]

        def spikes_of(device_name):
            return [
                float(t)
                for train in spiketrains
                if train.annotations.get("bsb_device_name") == device_name
                for t in train
            ]

        sr_exc, sr_inh = spikes_of("sr_exc"), spikes_of("sr_inh")
        self.assertTrue(sr_exc, "the excitatory recorder saw nothing")
        self.assertTrue(sr_inh, "the inhibitory recorder saw nothing")

        n_exc = sum(len(ids) for ids in targets["sr_exc"].values())
        n_inh = sum(len(ids) for ids in targets["sr_inh"].values())
        rate_ex = len(sr_exc) / simcfg.duration * 1000.0 / n_exc
        rate_in = len(sr_inh) / simcfg.duration * 1000.0 / n_inh

        # These are temporary circular values, taken from the output. May be incorrect.
        self.assertAlmostEqual(rate_in, 34.2, delta=1)
        self.assertAlmostEqual(rate_ex, 34.2, delta=1)
