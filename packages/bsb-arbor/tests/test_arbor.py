import unittest
from collections import defaultdict

from bsb import MPI, Configuration, Scaffold
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
        # One spiketrain per targeted cell; group them back per device.
        by_device = defaultdict(list)
        for st in spiketrains:
            by_device[st.annotations["bsb_device_name"]].append(st)
        exc_trains = by_device["sr_exc"]
        inh_trains = by_device["sr_inh"]

        self.assertTrue(exc_trains)
        self.assertTrue(inh_trains)

        spikes_ex = sum(len(st) for st in exc_trains)
        spikes_in = sum(len(st) for st in inh_trains)
        rate_ex = spikes_ex / simcfg.duration * 1000.0 / len(exc_trains)
        rate_in = spikes_in / simcfg.duration * 1000.0 / len(inh_trains)

        # These are temporary circular values, taken from the output. May be incorrect.
        self.assertAlmostEqual(rate_in, 34.2, delta=1)
        self.assertAlmostEqual(rate_ex, 34.2, delta=1)
