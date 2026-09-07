import abc
import typing

from .. import config

if typing.TYPE_CHECKING:  # pragma: nocover
    from .adapter import SimulationData, SimulatorAdapter
    from .results import SimulationResult
    from .simulation import Simulation


@config.dynamic(attr_name="strategy", auto_classmap=True)
class AfterPrepareHook(abc.ABC):
    """
    Hook that runs once the simulation it is configured on has been prepared, before
    it is run.

    Its counterpart to :class:`.AfterSimulationHook`: this one sees the simulation
    the backend has just built and can still change it, where that one sees what the
    run produced.

    The hook runs on every node that took part in preparing the simulation, so a
    hook that writes output is responsible for its own MPI awareness, through
    ``adapter.comm``.
    """

    name: str = config.attr(key=True)

    @abc.abstractmethod
    def postprocess(
        self,
        adapter: "SimulatorAdapter",
        simulation: "Simulation",
        simdata: "SimulationData",
    ):  # pragma: nocover
        """
        Process the prepared simulation.

        :param adapter: Adapter that prepared the simulation.
        :type adapter: ~bsb.simulation.adapter.SimulatorAdapter
        :param simulation: Simulation configuration that was prepared.
        :type simulation: ~bsb.simulation.simulation.Simulation
        :param simdata: What the backend built for it: its populations, connections
            and devices.
        :type simdata: ~bsb.simulation.adapter.SimulationData
        """
        pass


@config.dynamic(attr_name="strategy", auto_classmap=True)
class AfterSimulationHook(abc.ABC):
    """
    Hook that runs after the simulation it is configured on has finished and its
    results have been collected.

    The hook runs on every node that took part in the simulation, so hooks that
    write output are responsible for their own MPI awareness, through
    ``adapter.comm``.
    """

    name: str = config.attr(key=True)

    @abc.abstractmethod
    def postprocess(
        self,
        adapter: "SimulatorAdapter",
        simulation: "Simulation",
        result: "SimulationResult",
    ):  # pragma: nocover
        """
        Process the outcome of the simulation.

        :param adapter: Adapter that ran the simulation. The simulator is still
            set up at this point, so backend state can be inspected here.
        :type adapter: ~bsb.simulation.adapter.SimulatorAdapter
        :param simulation: Simulation configuration that was run.
        :type simulation: ~bsb.simulation.simulation.Simulation
        :param result: Collected results of the simulation.
        :type result: ~bsb.simulation.results.SimulationResult
        """
        pass


__all__ = ["AfterPrepareHook", "AfterSimulationHook"]
