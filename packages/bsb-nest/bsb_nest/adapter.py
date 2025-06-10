import contextlib
import sys
import typing

import nest
from bsb import (
    AdapterError,
    AdapterProgress,
    SimulationData,
    SimulationResult,
    SimulatorAdapter,
    report,
    warn,
)
from neo import SpikeTrain
from tqdm import tqdm

from .exceptions import KernelWarning, NestConnectError, NestModelError, NestModuleError

if typing.TYPE_CHECKING:
    from .simulation import NestSimulation


class NestResult(SimulationResult):
    def record(self, nc, **annotations):
        recorder = nest.Create("spike_recorder", params={"record_to": "memory"})
        nest.Connect(nc, recorder)

        def flush(segment):
            events = recorder.events[0]

            segment.spiketrains.append(
                SpikeTrain(
                    events["times"],
                    array_annotations={"senders": events["senders"]},
                    t_stop=nest.biological_time,
                    units="ms",
                    **annotations,
                )
            )

        self.create_recorder(flush)


class NestAdapter(SimulatorAdapter):
    def __init__(self, comm=None):
        super().__init__(comm=comm)
        self.loaded_modules = set()

    def simulate(self, *simulations, post_prepare=None):
        try:
            self.reset_kernel()
            return super().simulate(*simulations, post_prepare=post_prepare)
        finally:
            self.reset_kernel()

    def prepare(self, simulation):
        """
        Prepare the simulation environment in NEST.

        This method initializes internal data structures and performs all
        setup steps required before running the simulation:

        - Loads and installs required NEST modules.
        - Applies simulation-level settings (e.g., resolution, verbosity, seed).
        - Creates neuron populations based on cell models.
        - Establishes connectivity between neurons using connection models.
        - Instantiates devices (e.g., recorders, stimuli) used in the simulation.

        If any error occurs during preparation, the corresponding internal state
        is cleaned up to avoid partial setups.

        :param simulation: The simulation configuration to prepare.
        :type simulation: NestSimulation
        :returns: The prepared simulation data associated with the given simulation.
        :rtype: bsb.simulation.adapter.SimulationData
        """
        self.simdata[simulation] = SimulationData(
            simulation, result=NestResult(simulation)
        )
        try:
            report("Installing  NEST modules...", level=2)
            self.load_modules(simulation)
            self.set_settings(simulation)
            report("Creating neurons...", level=2)
            self.create_neurons(simulation)
            report("Creating connections...", level=2)
            self.connect_neurons(simulation)
            report("Creating devices...", level=2)
            self.create_devices(simulation)
            return self.simdata[simulation]
        except Exception:
            del self.simdata[simulation]
            raise

    def reset_kernel(self):
        nest.ResetKernel()
        # Reset which modules we should consider explicitly loaded by the user
        # to appropriately warn them when they load them twice.
        self.loaded_modules = set()

    def run(self, *simulations):
        unprepared = [sim for sim in simulations if sim not in self.simdata]
        if unprepared:
            raise AdapterError(f"Unprepared for simulations: {', '.join(unprepared)}")
        report("Simulating...", level=2)
        duration = max(sim.duration for sim in simulations)
        progress = AdapterProgress(duration)
        try:
            with nest.RunManager():
                for oi, i in progress.steps(step=1):
                    nest.Run(i - oi)
                    progress.tick(i)
        finally:
            results = [self.simdata[sim].result for sim in simulations]
            for sim in simulations:
                del self.simdata[sim]
        progress.complete()
        report("Simulation done.", level=2)
        return results

    def load_modules(self, simulation):
        for module in simulation.modules:
            try:
                nest.Install(module)
                self.loaded_modules.add(module)
            except Exception as e:
                if e.errorname == "DynamicModuleManagementError":
                    if "loaded already" in e.message:
                        # Modules stay loaded in between `ResetKernel` calls.
                        # If the module is not in the `loaded_modules` set, then
                        # it's the first time this `reset`/`prepare` cycle,
                        # and there is no user-side issue.
                        if module in self.loaded_modules:
                            warn(f"Already loaded '{module}'.", KernelWarning)
                    elif "file not found" in e.message:
                        raise NestModuleError(f"Module {module} not found") from None
                    else:
                        raise
                else:
                    raise

    def create_neurons(self, simulation):
        """
        Create a population of nodes in the NEST simulator based on the cell model
        configurations.
        """
        simdata = self.simdata[simulation]
        for cell_model in simulation.cell_models.values():
            simdata.populations[cell_model] = cell_model.create_population(simdata)

    def connect_neurons(self, simulation):
        """
        Connect the cells in NEST according to the connection model configurations
        """
        simdata = self.simdata[simulation]
        iter = simulation.connection_models.values()
        if self.comm.get_rank() == 0:
            iter = tqdm(iter, desc="", file=sys.stdout)
        for connection_model in iter:
            with contextlib.suppress(AttributeError):
                # Only rank 0 should report progress bar
                iter.set_description(connection_model.name)
            cs = simulation.scaffold.get_connectivity_set(
                connection_model.tag or connection_model.name
            )
            try:
                pre_nodes = simdata.populations[simulation.get_model_of(cs.pre_type)]
            except KeyError:
                raise NestModelError(f"No model found for {cs.pre_type}") from None
            try:
                post_nodes = simdata.populations[simulation.get_model_of(cs.post_type)]
            except KeyError:
                raise NestModelError(f"No model found for {cs.post_type}") from None
            try:
                simdata.connections[connection_model] = (
                    connection_model.create_connections(
                        simdata, pre_nodes, post_nodes, cs, self.comm
                    )
                )
            except Exception:
                raise NestConnectError(
                    f"{connection_model} error during connect."
                ) from None

    def create_devices(self, simulation):
        simdata = self.simdata[simulation]
        for device_model in simulation.devices.values():
            device_model.implement(self, simulation, simdata)

    def set_settings(self, simulation: "NestSimulation"):
        nest.set_verbosity(simulation.verbosity)
        nest.resolution = simulation.resolution
        nest.overwrite_files = True
        if simulation.seed is not None:
            nest.rng_seed = simulation.seed

    def check_comm(self):
        if nest.NumProcesses() != self.comm.get_size():
            raise RuntimeError(
                f"NEST is managing {nest.NumProcesses()} processes, but "
                f"{self.comm.get_size()} were detected. Please check your MPI setup."
            )
