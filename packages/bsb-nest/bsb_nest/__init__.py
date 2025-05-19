"""
NEST simulation adapter for the BSB framework.
"""

from bsb import SimulationBackendPlugin

from .adapter import NestAdapter
from .devices import (
    DCGenerator,
    Multimeter,
    PoissonGenerator,
    SinusoidalPoissonGenerator,
    SpikeRecorder,
)
from .simulation import NestSimulation

__plugin__ = SimulationBackendPlugin(Simulation=NestSimulation, Adapter=NestAdapter)

__all__ = [
    "DCGenerator",
    "Multimeter",
    "NestAdapter",
    "NestSimulation",
    "PoissonGenerator",
    "SinusoidalPoissonGenerator",
    "SpikeRecorder",
]
