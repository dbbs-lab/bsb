"""
NEURON simulator adapter for the BSB framework.
"""

from bsb import SimulationBackendPlugin

from .adapter import NeuronAdapter
from .devices import (
    CurrentClamp,
    IonRecorder,
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
    "IonRecorder",
    "SpikeGenerator",
    "SynapseRecorder",
    "VoltageClamp",
    "VoltageRecorder",
    "NeuronSimulation",
]
