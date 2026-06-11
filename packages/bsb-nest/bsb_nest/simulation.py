from bsb import Simulation, config, types

from .cell import NestCell
from .connection import NestConnection
from .device import NestDevice


@config.node
class NestSimulation(Simulation):
    """
    Interface between the scaffold model and the NEST simulator.
    """

    modules = config.list(type=str)
    """List of NEST modules to load at the beginning of the simulation"""
    threads = config.attr(type=types.int(min=1), default=1)
    """Number of threads to use during simulation"""
    resolution = config.attr(type=types.float(min=0.0), required=True)
    """Simulation time step size in milliseconds"""
    verbosity = config.attr(type=str, default="M_ERROR")
    """NEST verbosity level"""
    seed = config.attr(type=int, default=None)
    """Random seed for the simulations"""

    cell_models: config._attrs.cfgdict[NestCell] = config.dict(
        type=NestCell, required=True
    )
    """Dictionary of cell models in the simulation."""
    connection_models: config._attrs.cfgdict[NestConnection] = config.dict(
        type=NestConnection, required=True
    )
    """Dictionary of connection models in the simulation."""
    devices: config._attrs.cfgdict[NestDevice] = config.dict(
        type=NestDevice, required=True
    )
    """Dictionary of devices in the simulation."""
