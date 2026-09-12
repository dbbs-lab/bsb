import unittest

from bsb import MPI, Configuration, Scaffold
from bsb.simulation.results import iter_recordings
from bsb_test import RandomStorageFixture, get_test_config_tree


def _population_rate(block, device, duration):
    """
    Mean firing rate over a device's targets, in Hz.

    Spikes are recorded one train per cell, so the population's spikes are the
    trains of that device summed; cells that never fired have no train at all,
    which is why the divisor is the device's target count and not the number of
    trains.
    """
    recordings = list(iter_recordings(block, device=device))
    assert recordings, f"no recordings for device {device!r}"
    n_spikes = sum(len(recording.signal) for recording in recordings)
    pop_size = recordings[0].signal.annotations["pop_size"]
    return n_spikes / duration * 1000.0 / pop_size


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

        rate_ex = _population_rate(result.block, "sr_exc", simcfg.duration)
        rate_in = _population_rate(result.block, "sr_inh", simcfg.duration)

        # These are temporary circular values, taken from the output. May be incorrect.
        self.assertAlmostEqual(rate_in, 34.2, delta=1)
        self.assertAlmostEqual(rate_ex, 34.2, delta=1)
