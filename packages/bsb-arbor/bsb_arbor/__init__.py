"""
Arbor simulation adapter for the BSB framework
"""

from bsb import SimulationBackendPlugin

from . import devices
from .adapter import ArborAdapter
from .simulation import ArborSimulation

__version__ = "4.1.1"
__plugin__ = SimulationBackendPlugin(Simulation=ArborSimulation, Adapter=ArborAdapter)
