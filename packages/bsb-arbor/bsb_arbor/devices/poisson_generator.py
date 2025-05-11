import arbor
from arbor import units as U
from bsb import config

from ..connection import Receiver
from ..device import ArborDevice


@config.node
class PoissonGenerator(ArborDevice, classmap_entry="poisson_generator"):
    record = config.attr(type=bool, default=True)
    """Flag to save the spikes generated to file."""
    rate = config.attr(type=float, required=True)
    """Frequency of the poisson generator."""
    weight = config.attr(type=float, required=True)
    """Weight of the connection between the device and its target."""
    delay = config.attr(type=float, required=True)
    """Delay of the transmission between the device and its target."""

    def implement_probes(self, simdata, gid):
        return []

    def implement_generators(self, simdata, gid):
        target = Receiver(self, None, [-1, -1], [-1, -1], 0).on()
        gen = arbor.event_generator(
            target,
            self.weight,
            arbor.poisson_schedule(tstart=0 * U.ms, freq=self.rate * U.Hz, seed=gid),
        )
        return [gen]
