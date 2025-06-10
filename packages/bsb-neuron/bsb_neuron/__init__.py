"""
NEURON simulator adapter for the BSB framework.
"""

from bsb import SimulationBackendPlugin

from .adapter import NeuronAdapter
from .devices import (
    CurrentClamp,
    SpikeGenerator,
    SynapseRecorder,
    VoltageClamp,
    VoltageRecorder,
)
from .simulation import NeuronSimulation

__plugin__ = SimulationBackendPlugin(Simulation=NeuronSimulation, Adapter=NeuronAdapter)

__all__ = [
    "NeuronAdapter",
    "CurrentClamp",
    "SpikeGenerator",
    "SynapseRecorder",
    "VoltageClamp",
    "VoltageRecorder",
    "NeuronSimulation",
]
