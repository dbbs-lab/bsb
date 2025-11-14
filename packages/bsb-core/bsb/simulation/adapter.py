import abc
import os
import sys
import typing
from contextlib import ExitStack
from time import time

from tqdm import tqdm

from bsb import AttributeMissingError, SimulationResult, options

from ..services.mpi import MPIService

if typing.TYPE_CHECKING:  # pragma: nocover
    from ..storage import PlacementSet
    from .cell import CellModel
    from .simulation import Simulation


class FixedStepProgressController:
    def __init__(self, simulations, adapter, step=1):
        self._status = 0
        self._adapter = adapter
        self._start = self._last_tick = time()
        self._step = step
        self._sim_name = [sim._name for sim in simulations]
        self._use_tty = os.isatty(sys.stdout.fileno()) and sum(os.get_terminal_size())

        def silent():
            self._status = self._adapter.current_checkpoint

        if self._use_tty:
            if not self._adapter.comm.get_rank():
                self.run_checkpoint = self.use_bar
            else:
                self.run_checkpoint = silent
        else:
            if self._adapter.comm.get_rank():
                self.run_checkpoint = silent

    def get_next_checkpoint(self):
        return self._status + self._step

    def run_checkpoint(self):
        now = time()
        self._status = self._adapter.current_checkpoint
        tic = now - self._last_tick
        el_time = now - self._start
        duration = self._adapter._duration
        msg = f"Simulation {self._sim_name} | progress: {self._status:.2f} "
        msg += f"elapsed: {el_time:.2f}s - last step time: {tic:.2f}s - "
        msg += f"exectuted: {(self._status / duration) * 100:.2f}%"
        print(msg)
        self._last_tick = now

    def use_bar(self):
        if not self._status:
            self._progress_bar = tqdm(total=self._adapter._duration)
            self._progress_bar.update(self._adapter.current_checkpoint - self._status)
        elif self._adapter.current_checkpoint == self._adapter._duration:
            self._progress_bar.update(self._adapter.current_checkpoint - self._status)
            self._progress_bar.close()
        else:
            self._progress_bar.update(self._adapter.current_checkpoint - self._status)
        self._status = self._adapter.current_checkpoint


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

        self.simdata: dict[Simulation, SimulationData] = dict()
        self.comm = MPIService(comm)
        self._controllers = []
        self._duration = None
        self.current_checkpoint = 0

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
            if options.sim_console_progress:
                listener = FixedStepProgressController(
                    simulations, self, options.sim_console_progress
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
    def prepare(self, simulation):  # pragma: nocover
        """
        Reset the simulation backend and prepare for the given simulation.

        :param simulation: The simulation configuration to prepare.
        :type simulation: ~bsb.simulation.simulation.Simulation
        :return: Prepared simulation data.
        :rtype: SimulationData
        """
        pass

    @abc.abstractmethod
    def run(self, *simulations):  # pragma: nocover
        """
        Fire up the prepared adapter.

        :param simulations: One or a list of simulation configurations to simulate.
        :type simulations: ~bsb.simulation.simulation.Simulation
        :return: List of simulation results.
        :rtype: list[~bsb.simulation.results.SimulationResult]
        """
        pass

    def get_next_checkpoint(self):
        while self.current_checkpoint < self._duration:
            checkpoints = [
                controller.get_next_checkpoint() for controller in self._controllers
            ]
            # Filter out invalid "regressive" checkpoints,
            # and default to the end of the simulation
            chkp_noregressive = [
                checkpoint
                for checkpoint in checkpoints
                if checkpoint > self.current_checkpoint
            ]
            self.current_checkpoint = min(chkp_noregressive, default=self._duration)
            participants = [
                self._controllers[i]
                for i, checkpoint in enumerate(checkpoints)
                if checkpoint == self.current_checkpoint
            ]
            yield (self.current_checkpoint, participants)

    def execute_checkpoints(self, controllers):
        for controller in controllers:
            controller.run_checkpoint()

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
                if hasattr(component, "run_checkpoint"):
                    self._controllers.append(component)
                else:
                    raise AttributeMissingError(
                        f"Device {component.name} is configured to be a controller "
                        f"but run_checkpoint is not defined"
                    )


__all__ = [
    "FixedStepProgressController",
    "SimulationData",
    "SimulatorAdapter",
]
