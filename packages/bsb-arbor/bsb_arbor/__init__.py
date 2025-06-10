"""
Arbor simulation adapter for the BSB framework.
"""

from bsb import SimulationBackendPlugin

from .adapter import ArborAdapter
from .devices import PoissonGenerator, Probe, SpikeRecorder
from .simulation import ArborSimulation

__plugin__ = SimulationBackendPlugin(Simulation=ArborSimulation, Adapter=ArborAdapter)


__all__ = [
    "PoissonGenerator",
    "Probe",
    "SpikeRecorder",
    "ArborAdapter",
    "ArborSimulation",
]
