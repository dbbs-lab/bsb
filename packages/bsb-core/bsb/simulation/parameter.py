import abc
import sys
import typing

import numpy as np

from .. import config
from ..config import types
from ..config.types import TypeHandler
from ..exceptions import ConfigurationError

if typing.TYPE_CHECKING:  # pragma: nocover
    from ..morphologies import Morphology
    from ..storage.interfaces import ConnectivitySet, PlacementSet
    from .simulation import Simulation


@config.node
class Parameter(abc.ABC):  # noqa: B024  (see `compute` note below)
    """
    Base class for anything that answers "what is the value of this model parameter?".

    A parameter is configured like any other node and computes its values when the
    simulation is loaded. What it is computed *over* is what varies, so this base
    declares no :meth:`compute` signature; each arity below declares its own, and a
    parameter is only accepted where its arity fits.

    It is an :class:`abc.ABC` without abstract methods on purpose: subclasses need
    the abstract machinery for the ``compute`` they each declare, and inheriting it
    from here is what keeps one metaclass across the whole hierarchy.
    """

    name: str = config.attr(key=True)
    """Name of the model parameter this computes, taken from its configuration key."""

    is_constant: bool = False
    """
    Whether this yields a single value rather than one per element.

    Consumers use it to decide whether to broadcast, or to hand the value straight to
    a simulator that broadcasts on their behalf.
    """


@config.node
class Constant(Parameter):
    """
    A parameter that yields one value, whatever it is asked to compute over.

    Written as a bare value (``{"C_m": 250.0}``) rather than as a node, and accepted
    wherever a parameter of any arity is; it ignores the arguments it is handed.
    """

    is_constant = True

    value = config.attr(type=types.or_(types.list_or_scalar(types.number()), str))
    """The value to assign."""

    def __init__(self, value=None, /, **kwargs):
        # Primes the node from the shorthand form, where the value is written directly
        # instead of under a `value` key.
        if value is not None:
            self.value = value

    def compute(self, *args, **kwargs):
        return self.value


@config.dynamic(attr_name="strategy", auto_classmap=True)
class CellParameter(Parameter):
    """
    A parameter computed once per cell of a placement set.
    """

    @abc.abstractmethod
    def compute(
        self, simulation: "Simulation", ps: "PlacementSet"
    ) -> "np.ndarray":  # pragma: nocover
        """
        Compute one value per cell in ``ps``, in placement set order.

        :param simulation: The simulation being prepared.
        :param ps: The placement set of the cell model this is configured on.
        :returns: One value per cell.
        """
        pass


@config.dynamic(attr_name="strategy", auto_classmap=True)
class PointParameter(Parameter):
    """
    A parameter computed once per point of a cell's morphology.

    Points are addressed the way BSB addresses morphologies everywhere else, as
    ``(branch, point)``. How a simulator discretises a morphology is its own concern;
    an adapter maps points onto whatever its backend builds.
    """

    @abc.abstractmethod
    def compute(
        self,
        simulation: "Simulation",
        ps: "PlacementSet",
        cell_id: int,
        morphology: "Morphology",
    ) -> "np.ndarray":  # pragma: nocover
        """
        Compute one value per point of ``morphology``, in flattened branch order.

        :param simulation: The simulation being prepared.
        :param ps: The placement set the cell belongs to.
        :param cell_id: Index of the cell within ``ps``.
        :param morphology: The cell's morphology.
        :returns: One value per morphology point.
        """
        pass


@config.dynamic(attr_name="strategy", auto_classmap=True)
class ConnectionParameter(Parameter):
    """
    A parameter computed once per connection of a connectivity set.
    """

    @abc.abstractmethod
    def compute(
        self,
        simulation: "Simulation",
        cs: "ConnectivitySet",
        pre_locs: "np.ndarray",
        post_locs: "np.ndarray",
    ) -> "np.ndarray":  # pragma: nocover
        """
        Compute one value per connection, in the order the locations are given.

        :param simulation: The simulation being prepared.
        :param cs: The connectivity set of the connection model this is configured on.
        :param pre_locs: Presynaptic locations, as ``(cell, branch, point)`` rows.
        :param post_locs: Postsynaptic locations, as ``(cell, branch, point)`` rows.
        :returns: One value per connection.
        """
        pass


@config.node
class DistanceDelayParameter(ConnectionParameter, classmap_entry="distance_delay"):
    """
    Transmission delay derived from the distance between the connected somata.

    The delay is the soma-to-soma distance divided by the axonal conduction speed,
    floored at the simulation's resolution so no connection is asked to deliver
    faster than the simulation can step.
    """

    axon_speed: float = config.attr(
        type=types.float(min=sys.float_info.min), required=True
    )
    """Axonal conduction speed, in the network's spatial units per millisecond."""

    def compute(self, simulation, cs, pre_locs, post_locs):
        pre_pos = self._positions(cs.pre_type)[pre_locs[:, 0]]
        post_pos = self._positions(cs.post_type)[post_locs[:, 0]]
        distance = np.linalg.norm(pre_pos - post_pos, axis=-1)
        return np.maximum(distance / self.axon_speed, simulation.resolution)

    def _positions(self, cell_type):
        # `compute` runs once per block of connections and reads whole position sets,
        # so they are held for the duration of the run rather than reloaded per block.
        # Cleared by `drop_caches` when the run ends, so a rerun sees current data.
        cache = self.__dict__.setdefault("_position_cache", {})
        if cell_type.name not in cache:
            cache[cell_type.name] = cell_type.get_placement_set().load_positions()
        return cache[cell_type.name]

    def drop_caches(self):
        self.__dict__.pop("_position_cache", None)


class ParameterizedModel:
    """
    Mixin for models whose parameters can be written in more than one notation.

    A backend is free to keep whatever spellings its users already know — a
    first-class ``weight`` attribute, a catch-all of constants, an explicit
    ``parameters`` block — and collect them here into one mapping, so everything
    downstream deals with parameters and nothing else.
    """

    def get_parameter_groups(self) -> "typing.Iterable[typing.Mapping]":
        """
        The notations to collect, in precedence order.

        Override to add a backend's own spellings. Later groups do not override
        earlier ones; naming the same parameter twice is a configuration error,
        because there is no reading of it that is not a mistake.
        """
        return (self.parameters,)

    def get_parameters(self) -> dict:
        """
        Every parameter configured on this model, whichever notation it was written
        in, keyed by the model parameter it sets.
        """
        merged = {}
        for group in self.get_parameter_groups():
            for key, param in group.items():
                if key in merged:
                    raise ConfigurationError(
                        f"Parameter '{key}' of {self} is configured twice; "
                        "give it in one place only."
                    )
                merged[key] = param
        return merged

    def compute_parameters(self, *args, **kwargs) -> dict:
        """
        Every parameter of this model, computed into the values a backend assigns.

        The consumption counterpart of :meth:`get_parameters`: the arguments are
        whatever the arity of this model's parameters takes, and a constant ignores
        them.

        :returns: The configured parameters, keyed by name, as plain values.
        """
        return {
            name: param.compute(*args, **kwargs)
            for name, param in self.get_parameters().items()
        }


class constant(TypeHandler):
    """
    Cast a configuration value to a :class:`.Constant`.

    The narrow counterpart of :class:`.parameter`, for notations documented as
    holding constants. It refuses a computed parameter rather than silently
    accepting one, so ``constants`` keeps meaning what it says and the wider
    ``parameters`` block is the one place a strategy belongs.
    """

    def __call__(self, value, _key=None, _parent=None):
        if isinstance(value, dict) and "strategy" in value:
            raise TypeError(
                f"'{_key}' is a computed parameter, which belongs in `parameters` "
                "rather than in `constants`."
            )
        if isinstance(value, Parameter):
            return value
        return Constant(value, _key=_key, _parent=_parent)

    @property
    def __name__(self):  # pragma: nocover
        return "constant"

    def __inv__(self, value):
        return value.value if getattr(value, "is_constant", False) else value


class parameter(TypeHandler):
    """
    Cast a configuration value to a :class:`.Parameter` of a given arity.

    Keeps the shorthands a value can be written in, and homogenizes them into
    parameter nodes so consumers only ever deal with one thing:

    * a bare value becomes a :class:`.Constant`;
    * a node with a ``strategy`` key is cast to that strategy of ``base``;
    * an already-constructed parameter passes through.

    Casting through a type handler, rather than typing the attribute as ``base``
    itself, is what lets one :class:`.Constant` be accepted at every arity without
    needing a separate constant class per arity.
    """

    def __init__(self, base=Parameter):
        self._base = base

    def __call__(self, value, _key=None, _parent=None):
        if isinstance(value, Parameter):
            return value
        if isinstance(value, dict) and "strategy" in value:
            return self._base(**value, _key=_key, _parent=_parent)
        return Constant(value, _key=_key, _parent=_parent)

    @property
    def __name__(self):  # pragma: nocover
        return f"{self._base.__name__.lower()}"

    def __inv__(self, value):
        # Constants were written as bare values, so they invert back to bare values
        # rather than to a node the user never wrote.
        if getattr(value, "is_constant", False):
            return value.value
        return value


__all__ = [
    "CellParameter",
    "ConnectionParameter",
    "Constant",
    "constant",
    "DistanceDelayParameter",
    "Parameter",
    "ParameterizedModel",
    "PointParameter",
    "parameter",
]
