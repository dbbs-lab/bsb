import psutil
from bsb import Simulation, config, types

from .cell import ArborCell
from .connection import ArborConnection
from .device import ArborDevice


@config.node
class ArborSimulation(Simulation):
    """
    Interface between the scaffold model and the Arbor simulator.
    """

    resolution = config.attr(type=types.float(min=0.0), default=0.1)
    """Simulation time step size in milliseconds."""
    profiling = config.attr(type=bool)
    """Flag to perform profiling during the simulation."""
    cell_models: config._attrs.cfgdict[ArborCell] = config.dict(
        type=ArborCell, required=True
    )
    """Dictionary of cell models in the simulation."""
    connection_models: config._attrs.cfgdict[ArborConnection] = config.dict(
        type=ArborConnection, required=True
    )
    """Dictionary of connection models in the simulation."""
    devices: config._attrs.cfgdict[ArborDevice] = config.dict(
        type=ArborDevice, required=True
    )
    """Dictionary of devices in the simulation."""

    @config.property(default=1)
    def threads(self):
        return self._threads

    @threads.setter
    def threads(self, value):
        self._threads = value if value != "all" else psutil.cpu_count(logical=False)
