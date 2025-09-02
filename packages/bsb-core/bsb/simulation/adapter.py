import abc
import os
import sys
import types
import typing
from contextlib import ExitStack
from time import time

import numpy as np

from bsb import AttributeMissingError, SimulationResult, report

from ..services.mpi import MPIService

if typing.TYPE_CHECKING:
    from ..storage import PlacementSet
    from .cell import CellModel
    from .simulation import Simulation


class AdapterController(abc.ABC):
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


class BasicSimulationListener(AdapterController):
    def __init__(self, adapter, step=1, silent=False):
        self._status = 0
        self._adapter = adapter
        self._start = self._last_tick = time()
        self._step = step
        self.need_flush = False
        self._sim_name = [sim._name for sim in self._adapter.simdata]
        if silent:
            self.progress = self.silently

    def get_next_checkpoint(self):
        return self._status + self._step

    def progress(self, kwargs=None):
        now = time()
        tic = now - self._last_tick
        el_time = now - self._start
        duration = self._adapter._duration
        msg = f"Simulation {self._sim_name} | progress: {self._status} - "
        msg += f"elapsed: {el_time:.2f}s - last step time: {tic:.2f}s - "
        msg += f"exectuted: {(self._status / duration) * 100:.2f}%"
        report(msg, level=2)
        self._last_tick = now
        self._status += self._step
        return self._status

    def silently(self, kwargs=None):
        self._status += self._step
        return self._status


class SimulationData:
    def __init__(self, simulation: "Simulation", result=None):
        self.chunks = None
        self.populations = dict()
        self.placement: dict[CellModel, PlacementSet] = {
            model: model.get_placement_set()
            for model in simulation.cell_models.values()
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
        self.pbar = False

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
            return self.collect(results)

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
        while self._sim_checkpoint < self._duration:
            checkpoints = [cnt.get_next_checkpoint() for cnt in self._controllers]
            self._sim_checkpoint = np.min(checkpoints)
            cnt_ids = np.where(checkpoints == self._sim_checkpoint)[0]
            yield (self._sim_checkpoint, cnt_ids)

    def execute(self, controller_ids, **kwargs):
        flush_point = False
        for i in controller_ids:
            self._controllers[i].progress(kwargs=kwargs)  # self._controllers[i]()
            flush_point = flush_point or self._controllers[i].need_flush
        return flush_point

    def collect(self, results):
        """
        Collect the output the simulations that reached a checkpoint.

        :return: Collected simulation results.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        for result in results:
            result.flush()
        return results

    def add_progress_listener(self, listener):
        self._progress_listeners.append(listener)

    def load_controllers(self, simulation):
        if not self._progress_listeners:
            if os.isatty(sys.stdout.fileno()) and sum(os.get_terminal_size()):
                base_list = BasicSimulationListener(self, step=5, silent=True)
                self.pbar = True
            else:
                base_list = BasicSimulationListener(self, step=5)
                self.pbar = False
            self._progress_listeners.append(base_list)
        for listener in self._progress_listeners:
            if listener not in self._controllers:
                if hasattr(listener, "progress") and hasattr(
                    listener, "get_next_checkpoint"
                ):
                    self._controllers.append(listener)
                else:
                    raise AttributeMissingError(
                        f"The Simulation listener {listener} does not implement "
                        f"get_next_checkpoint or progress method,"
                        f"cannot use it as controller"
                    )
        for device in simulation.devices.values():
            if hasattr(device, "get_next_checkpoint"):
                if hasattr(device, "progress") and hasattr(device, "need_flush"):
                    self._controllers.append(device)
                else:
                    raise AttributeMissingError(
                        f"Device {device.name} is configured to be a controller "
                        f"but progress or need_flush attributes"
                        f" are not defined"
                    )


__all__ = [
    "AdapterProgress",
    "AdapterController",
    "BasicSimulationListener",
    "SimulationData",
    "SimulatorAdapter",
]
