import nest
from bsb import ConfigurationError, config
from neo import SpikeTrain

from ..device import NestDevice


@config.node
class SinusoidalPoissonGenerator(
    NestDevice, classmap_entry="sinusoidal_poisson_generator"
):
    rate = config.attr(type=float, required=True)
    """Rate of the poisson generator"""
    amplitude = config.attr(type=float, required=True)
    """Amplitude of the sinusoidal signal"""
    frequency = config.attr(type=float, required=True)
    """Frequency of the sinusoidal signal"""
    phase = config.attr(type=float, required=False, default=0.0)
    """Phase of the sinusoidal signal"""
    start = config.attr(type=float, required=False, default=0.0)
    """Activation time in ms"""
    stop = config.attr(type=float, required=False, default=None)
    """Deactivation time in ms. 
        If not specified, generator will last until the end of the simulation."""

    def boot(self):
        if self.stop is not None and self.stop <= self.start:
            raise ConfigurationError(
                f"Stop time (given: {self.stop}) must be greater than start time "
                f"(given: {self.start})."
            )

    def implement(self, adapter, simulation, simdata):
        nodes = self.get_target_nodes(adapter, simulation, simdata)
        params = {
            "rate": self.rate,
            "start": self.start,
            "amplitude": self.amplitude,
            "frequency": self.frequency,
            "phase": self.phase,
        }
        if self.stop is not None:
            params["stop"] = self.stop
        device = self.register_device(
            simdata, nest.Create("sinusoidal_poisson_generator", params=params)
        )
        sr = nest.Create("spike_recorder")
        nest.Connect(device, sr)
        self.connect_to_nodes(device, nodes)

        def recorder(segment):
            segment.spiketrains.append(
                SpikeTrain(
                    sr.events["times"],
                    units="ms",
                    array_annotations={"senders": sr.events["senders"]},
                    t_stop=simulation.duration,
                    device=self.name,
                    pop_size=len(nodes),
                )
            )

        simdata.result.create_recorder(recorder)
