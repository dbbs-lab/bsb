import arbor
from arbor import units as U
from bsb import config

from ..connection import Receiver
from ..device import ArborDevice


@config.node
class PoissonGenerator(ArborDevice, classmap_entry="poisson_generator"):
    record = config.attr(type=bool, default=True)
    rate = config.attr(type=float, required=True)
    weight = config.attr(type=float, required=True)
    delay = config.attr(type=float, required=True)

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
