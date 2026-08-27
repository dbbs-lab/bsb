import abc
import sys

import numpy as np

from .. import ConnectivitySet, PlacementSet, config, types


@config.dynamic(attr_name="type", auto_classmap=True, required=False)
class ParameterValue:
    def __init__(self, value=None, /, **kwargs):
        self._constant = value


@config.dynamic(attr_name="type", auto_classmap=True, required=False)
class Parameter:
    value: ParameterValue = config.attr(type=ParameterValue)


@config.dynamic(attr_name="strategy")
class CellParameter(abc.ABC):
    """
    Class for cell parameters to be computed during simulation loading.
    """

    name: str = config.attr(key=True)

    @abc.abstractmethod
    def compute(self, sim, ps: PlacementSet, id: int):  # pragma: nocover
        pass


@config.dynamic(attr_name="strategy")
class ConnectionParameter(abc.ABC):
    """
    Class for connection parameters to be computed during simulation loading.
    """

    name: str = config.attr(key=True)

    @abc.abstractmethod
    def compute(self, sim, cs: ConnectivitySet, pre_locs, post_locs):  # pragma: nocover
        pass


@config.node
class DistanceDelayParameter(ConnectionParameter):
    axon_speed = config.attr(type=types.float(min=sys.float_info.min), required=True)

    def compute(self, sim, cs, pre_locs, post_locs):
        pre_pos = cs.pre_type.get_placement_set().load_positions()[pre_locs[:, 0]]
        post_pos = cs.post_type.get_placement_set().load_positions()[post_locs[:, 0]]

        return np.maximum(
            np.linalg.norm(pre_pos - post_pos, axis=-1) / self.axon_speed, sim.resolution
        )


__all__ = [
    "CellParameter",
    "ConnectionParameter",
    "DistanceDelayParameter",
    "Parameter",
    "ParameterValue",
]
