import abc
import types
import typing
from contextlib import ExitStack
from time import time

import numpy as np

from ..services.mpi import MPIService
from .results import SimulationResult

if typing.TYPE_CHECKING:
    from ..storage import PlacementSet
    from .cell import CellModel
    from .simulation import Simulation


class AdapterController(abc.ABC):
    def __init__(self, start_t=None):
        self._status = start_t or 0

    @abc.abstractmethod
    def get_next_checkpoint(self):
        """method to implement that is needed for look for the next checkpoint
        :return: Next checkpoint time.
        :rtype: float
        """
        pass

    @abc.abstractmethod
    def progress(self):
        """method that the controller will use to advance to the next checkpoint
        :return: Next checkpoint time.
        :rtype: float
        """
        pass

    def complete(self):
        return


class AdapterProgress(AdapterController):
    def __init__(self, step, duration):
        self._step = step
        self._start = self._last_tick = time()
        self._ticks = 0
        self._duration = duration

    def tick(self, duration=None):
        """
        Report simulation progress.
        """
        now = time()
        tic = now - self._last_tick
        self._ticks += 1
        el = now - self._start
        args = {
            "progression": self._step,
            "time": time(),
            "duration": self._duration,
            "tick": tic,
            "elapsed": el,
        }

        progress = types.SimpleNamespace(**args)
        self._last_tick = now
        return progress

    def get_next_checkpoint(self, time):
        return self._status + self._step

    def progress(self):
        self._status += self._step
        return self._status


class BasicSimulationListener:
    def __init__(self, adapter, step):
        self._simulations_name = adapter.simdata.keys()
        self._comm = adapter.comm
        self._t_status = 0
        self._step = step or 1

    def get_next_checkpoint(self):
        return self._t_status + self._step


class SimulationData:
    def __init__(self, simulation: "Simulation", result=None):
        self.chunks = None
        self.populations = dict()
        self.placement: dict[CellModel, PlacementSet] = {
            model: model.get_placement_set() for model in simulation.cell_models.values()
        }
        self.connections = dict()
        self.devices = dict()
        if result is None:
            result = SimulationResult(simulation)
        self.result: SimulationResult = result


class SimulatorAdapter(abc.ABC):
    def __init__(self, comm=None):
        """
        :param comm: The mpi4py MPI communicator to use. Only nodes in the communicator
          will participate in the simulation. The first node will idle as the main node.
        """
        self._progress_listeners = []
        self.simdata: dict[Simulation, SimulationData] = dict()
        self.comm = MPIService(comm)
        self._controllers = []
        self._duration = None
        self._sim_checkpoint = 0

    def simulate(self, *simulations, post_prepare=None):
        """
        Simulate the given simulations.

        :param simulations: One or a list of simulation configurations to simulate.
        :type simulations: ~bsb.simulation.simulation.Simulation
        :param post_prepare: Optional callable to run after the simulations' preparation.
        :return: List of simulation results for each simulation run.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        with ExitStack() as context:
            for simulation in simulations:
                context.enter_context(simulation.scaffold.storage.read_only())
            alldata = []
            for simulation in simulations:
                data = self.prepare(simulation)
                alldata.append(data)
                for hook in simulation.post_prepare:
                    hook(self, simulation, data)
            if post_prepare:
                post_prepare(self, simulations, alldata)
            results = self.run(*simulations)
            return results

    @abc.abstractmethod
    def prepare(self, simulation):
        """
        Reset the simulation backend and prepare for the given simulation.

        :param simulation: The simulation configuration to prepare.
        :type simulation: ~bsb.simulation.simulation.Simulation
        :return: Prepared simulation data.
        :rtype: SimulationData
        """
        pass

    @abc.abstractmethod
    def run(self, *simulations):
        """
        Fire up the prepared adapter.

        :param simulations: One or a list of simulation configurations to simulate.
        :type simulations: ~bsb.simulation.simulation.Simulation
        :return: List of simulation results.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        pass

    def get_next_checkpoint(self):
        while self._sim_checkpoint < self.duration:
            checkpoints = [cnt.get_next_checkpoint() for cnt in self._controllers]
            self._sim_checkpoint = np.min(checkpoints)
            cnt_ids = np.where(checkpoints == self._sim_checkpoint)
            yield (self._sim_checkpoint, cnt_ids)

    def execute(self, controller_ids, *args):
        for i in controller_ids:
            self._controllers[i].progress(args)  # self._controllers[i]()

    def collect(self, results):
        """
        Collect the output the simulations that reached a checkpoint.

        :return: Collected simulation results.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        for result in results:
            result.flush()

    def add_progress_listener(self, listener):
        self._progress_listeners.append(listener)

    def load_controllers(self, simulation):
        if not self._progress_listeners:
            self._progress_listeners.append(BasicSimulationListener)
        for listener in self._progress_listeners:
            if hasattr(listener, "progress") and hasattr(listener, "get_next_checkpoint"):
                self._controllers.append(listener)
            else:
                raise TypeError(
                    f"The Simulation listener {listener} does not implement "
                    f"get_next_checkpoint or progress method,"
                    f"cannot use it as controller"
                )
        for device in simulation.devices.values():
            if hasattr(device, "get_next_checkpoint"):
                if hasattr(device, "progress"):
                    self._controllers.append(device)
                else:
                    raise TypeError(
                        f"Device {device.name} is configured to be a controller "
                        f"but progress method is not defined"
                    )


__all__ = ["AdapterProgress", "SimulationData", "SimulatorAdapter"]
