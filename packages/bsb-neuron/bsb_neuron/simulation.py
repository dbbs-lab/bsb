from bsb import Simulation, config, types

from .cell import NeuronCell
from .connection import NeuronConnection
from .device import NeuronDevice


@config.node
class NeuronSimulation(Simulation):
    """
    Interface between the scaffold model and the NEURON simulator.
    """

    initial = config.attr(type=float, default=-65.0)
    """Initial membrane potential for all neurons."""
    resolution = config.attr(type=types.float(min=0.0), default=0.1)
    """Simulation time step size in milliseconds."""
    temperature = config.attr(type=float, required=True)
    """Temperature of the circuit during simulation."""
    cell_models: config._attrs.cfgdict[NeuronCell] = config.dict(
        type=NeuronCell, required=True
    )
    """Dictionary of cell models in the simulation."""
    connection_models: config._attrs.cfgdict[NeuronConnection] = config.dict(
        type=NeuronConnection, required=True
    )
    """Dictionary of connection models in the simulation."""
    devices: config._attrs.cfgdict[NeuronDevice] = config.dict(
        type=NeuronDevice, required=True
    )
    """Dictionary of devices in the simulation."""
