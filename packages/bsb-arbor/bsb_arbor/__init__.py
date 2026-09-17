"""
Arbor simulation adapter for the BSB framework.
"""

from bsb import SimulationBackendPlugin

from .adapter import ArborAdapter
from .devices import PoissonGenerator, SpikeRecorder
from .simulation import ArborSimulation

__plugin__ = SimulationBackendPlugin(Simulation=ArborSimulation, Adapter=ArborAdapter)


__all__ = [
    "PoissonGenerator",
    "SpikeRecorder",
    "ArborAdapter",
    "ArborSimulation",
]
