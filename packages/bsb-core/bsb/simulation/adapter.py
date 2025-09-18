import abc
import os
import sys
import typing
from contextlib import ExitStack
from time import time

import numpy as np

from bsb import AttributeMissingError, SimulationResult, options, report

from ..services.mpi import MPIService

if typing.TYPE_CHECKING:
    from ..storage import PlacementSet
    from .cell import CellModel
    from .simulation import Simulation


class BasicSimulationListener:
    def __init__(self, simulations, adapter, step=1):
        self._status = 0
        self._adapter = adapter
        self._start = self._last_tick = time()
        self._step = step
        self._sim_name = [sim._name for sim in simulations]
        self._use_tty = os.isatty(sys.stdout.fileno()) and sum(os.get_terminal_size())
        if self._use_tty:
            self.progress = self.use_bar

    def get_next_checkpoint(self):
        return self._status + self._step

    def on_start(self):
        if self._use_tty:
            empty_lines = "\n" * self._adapter.comm.get_size()
            report(empty_lines, level=1)
        else:
            pass

    def progress(self, kwargs=None):
        now = time()
        tic = now - self._last_tick
        el_time = now - self._start
        duration = self._adapter._duration
        msg = f"Simulation {self._sim_name} | progress: {self._status} - "
        msg += f"elapsed: {el_time:.2f}s - last step time: {tic:.2f}s - "
        msg += f"exectuted: {(self._status / duration) * 100:.2f}%"
        report(msg, level=1)
        self._last_tick = now
        self._status += self._step
        return self._status

    def progress_bar(self, current_percent, rank, mpi_size):
        color = "\033[91m"  # red
        if current_percent > 33:
            color = "\033[93m"
        if current_percent > 66:
            color = "\033[92m"
        sys.stdout.write(
            "\x1b[1A" * (int(mpi_size) - rank)
            + "\r"
            + str(self._sim_name)
            + " ["
            + color
            + "%s" % ("-" * current_percent + " " * (100 - current_percent))
            + "\033[0m"
            + "] "
            + str(current_percent)
            + "%"
            + "\n" * (int(mpi_size) - rank)
        )
        sys.stdout.flush()

    def use_bar(self, kwargs=None):
        current_percent = int((self._status / self._adapter._duration) * 100)
        rank = self._adapter.comm.get_rank()
        mpi_size = self._adapter.comm.get_size()
        self.progress_bar(current_percent, rank, mpi_size)
        self._status += self._step
        return self._status


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
        # print(f" Rep CFlag : {} | Verbosity: {options.verbosity}")

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
            if options.simulation_report:
                listener = BasicSimulationListener(
                    simulations, self, options.simulation_report
                )
                self._controllers.append(listener)

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
            complete = np.append(
                checkpoints, self._duration
            )  # In case of no checkpoint provided
            self._sim_checkpoint = np.min(complete)
            cnt_ids = np.where(checkpoints == self._sim_checkpoint)[0]
            yield (self._sim_checkpoint, cnt_ids)

    def execute(self, controller_ids, **kwargs):
        for i in controller_ids:
            self._controllers[i].progress(kwargs=kwargs)

    def collect(self, results):
        """
        Collect the output the simulations that completed.

        :return: Collected simulation results.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        for result in results:
            result.flush()
        return results

    def implement_components(self, simulation):
        simdata = self.simdata[simulation]
        for component in simulation.get_components():
            component.implement(self, simulation, simdata)

    def load_controllers(self, simulation):
        for component in simulation.get_components():
            if hasattr(component, "get_next_checkpoint"):
                if hasattr(component, "progress"):
                    self._controllers.append(component)
                else:
                    raise AttributeMissingError(
                        f"Device {component.name} is configured to be a controller "
                        f"but progress is not defined"
                    )


__all__ = [
    "BasicSimulationListener",
    "SimulationData",
    "SimulatorAdapter",
]
