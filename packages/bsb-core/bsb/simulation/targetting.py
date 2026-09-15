import functools
import math
import typing

import numpy as np

from .. import config
from ..config import refs, types
from ..rng import RngConsumer

if typing.TYPE_CHECKING:  # pragma: nocover
    from ..cell_types import CellType
    from .cell import CellModel


def _target_name(targetting) -> str:
    """Name a targetting node by the device it belongs to, for seed derivation."""
    device = getattr(targetting, "_config_parent", None)
    return getattr(device, "name", None) or type(targetting).__name__


def _model_name(model) -> str:
    """Name whatever a target group is keyed by: a model, a cell type, or a string."""
    return getattr(model, "name", None) or str(model)


@config.dynamic(attr_name="strategy", default="all", auto_classmap=True)
class Targetting(RngConsumer):
    type: typing.Literal["cell"] | typing.Literal["connection"] = config.attr(
        type=types.in_(["cell", "connection"]), default="cell"
    )

    def get_placement_targets(self, simulation) -> dict:
        """
        The cells this targets, as local ids into each targeted cell model's
        placement set, sorted ascending.

        Backend agnostic: computed from the scaffold and the simulation's own
        configuration alone, so it needs no live run and no backend population to
        slice. That lets it be replayed after the fact, from a stored
        configuration, to work out which placed cell a recording belongs to — and
        it is sorted because at least one backend (NEST) refuses an unsorted index
        into a population, a requirement every override here has to satisfy too.

        :param simulation: The simulation this targetting belongs to.
        :type simulation: bsb.simulation.simulation.Simulation
        :returns: Local placement ids per targeted cell model, each sorted
            ascending.
        :rtype: dict[bsb.simulation.cell.CellModel, numpy.ndarray[int]]
        """
        if self.type != "cell":
            raise NotImplementedError(
                f"'{type(self).__name__}' targets connections, not cells; there is "
                "no placement id to resolve."
            )
        return {
            model: model.get_placement_set().load_ids()
            for model in simulation.cell_models.values()
        }

    def get_targets(self, adapter, simulation, simdata):
        if self.type == "cell":
            return {
                model: simdata.populations[model][ids]
                for model, ids in self.get_placement_targets(simulation).items()
            }
        elif self.type == "connection":
            return simdata.connections


@config.node
class CellTargetting(Targetting, classmap_entry="all"):
    @config.property
    def type(self):
        return "cell"


@config.node
class ConnectionTargetting(Targetting, classmap_entry="all_connections"):
    @config.property
    def type(self):
        return "connection"

    def get_targets(self, adapter, simulation, simdata):
        return simdata.connections


class CellModelFilter:
    cell_models: list["CellModel"] = config.reflist(
        refs.sim_cell_model_ref, required=False
    )

    def get_placement_targets(self, simulation):
        return {
            model: model.get_placement_set().load_ids()
            for model in simulation.cell_models.values()
            if not self.cell_models or model in self.cell_models
        }


class CellTypeFilter:
    cell_types: list["CellType"] = config.reflist(refs.cell_type_ref, required=False)
    only_local: bool = config.attr(type=bool, default=True)

    def _filtered_placement_sets(self, simulation, chunks=None):
        return {
            cell_name: cell_type.get_placement_set(chunks=chunks)
            for cell_name, cell_type in simulation.scaffold.cell_types.items()
            if not self.cell_types or cell_type in self.cell_types
        }

    def get_placement_targets(self, simulation):
        return {
            cell_name: ps.load_ids()
            for cell_name, ps in self._filtered_placement_sets(simulation).items()
        }

    def get_targets(self, adapter, simulation, simdata):
        chunks = simdata.chunks if self.only_local else None
        return self._filtered_placement_sets(simulation, chunks=chunks)


class FractionFilter:
    count = config.attr(
        type=int, required=types.mut_excl("fraction", "count", required=False)
    )
    fraction = config.attr(
        type=types.fraction(),
        required=types.mut_excl("fraction", "count", required=False),
    )

    def satisfy_fractions(self, targets):
        return {model: self._frac(model, data) for model, data in targets.items()}

    def _frac(self, model, data):
        take = None
        if self.count is not None:
            take = self.count
        if self.fraction is not None:
            take = math.floor(len(data) * self.fraction)
        if take is None:
            return data
        else:
            # Keyed on the device and the population it targets, so every rank draws
            # the same subset. Drawn unseeded, each rank picked its own, and a device
            # ended up connected to different cells on different ranks.
            rng = self.get_rng(key=("targetting", _target_name(self), _model_name(model)))
            # Select `take` elements from data with a boolean mask (otherwise a sorted
            # integer mask would be required)
            idx = np.zeros(len(data), dtype=bool)
            idx[rng.choice(len(data), take, replace=False)] = True
            return data[idx]

    @staticmethod
    def filter(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            return self.satisfy_fractions(f(self, *args, **kwargs))

        return wrapper


@config.node
class CellModelTargetting(
    CellModelFilter, FractionFilter, CellTargetting, classmap_entry="cell_model"
):
    """
    Targets all cells of certain cell models.
    """

    cell_models: list["CellModel"] = config.reflist(
        refs.sim_cell_model_ref, required=True
    )

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        return super().get_placement_targets(simulation)


@config.node
class RepresentativesTargetting(
    CellModelFilter, FractionFilter, CellTargetting, classmap_entry="representatives"
):
    """
    Targets all identifiers of certain cell types.
    """

    n: int = config.attr(type=int, default=1)

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        return {
            model: np.sort(
                ids[
                    self.get_rng(
                        key=("representatives", _target_name(self), _model_name(model))
                    ).choice(len(ids), size=self.n, replace=False)
                ]
            )
            for model, ids in super().get_placement_targets(simulation).items()
        }


@config.node
class ByIdTargetting(FractionFilter, CellTargetting, classmap_entry="by_id"):
    """
    Targets all given identifiers.
    """

    ids: dict[str, list[int]] = config.attr(
        type=types.dict(type=types.list(type=int)), required=True
    )

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        by_name = {
            model.name: model
            for model in simulation.cell_models.values()
            if len(model.get_placement_set())
        }

        dict_target = {}
        for model_name, ids in self.ids.items():
            if (model := by_name.get(model_name)) is not None:
                local_ids = model.get_placement_set().convert_to_local(ids)
                dict_target[model] = np.sort(np.asarray(local_ids))
        return dict_target


@config.node
class ByLabelTargetting(
    CellModelFilter, FractionFilter, CellTargetting, classmap_entry="by_label"
):
    """
    Targets all given labels.
    """

    labels: list[str] = config.attr(type=types.list(type=str), required=True)

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        return {
            model: ids[model.get_placement_set().get_label_mask(self.labels)]
            for model, ids in super().get_placement_targets(simulation).items()
        }


@config.node
class CylindricalTargetting(
    CellModelFilter, FractionFilter, CellTargetting, classmap_entry="cylinder"
):
    """
    Targets all cells in a cylinder along specified axis.
    """

    origin: np.ndarray[float] = config.attr(type=types.ndarray(shape=(2,), dtype=float))
    """
    Coordinates of the base of the cylinder for each non main axis.
    """
    axis: typing.Literal["x"] | typing.Literal["y"] | typing.Literal["z"] = config.attr(
        type=types.in_(["x", "y", "z"]), default="y"
    )
    """
    Main axis of the cylinder.
    """
    radius: float = config.attr(type=float, required=True)
    """
    Radius of the cylinder.
    """

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        """
        Target all or certain cells within a cylinder of specified radius.
        """
        if self.axis == "x":
            axes = [1, 2]
        elif self.axis == "y":
            axes = [0, 2]
        else:
            axes = [0, 1]
        return {
            model: ids[
                np.sum(
                    (model.get_placement_set().load_positions()[:, axes] - self.origin)
                    ** 2,
                    axis=1,
                )
                < self.radius**2
            ]
            for model, ids in super().get_placement_targets(simulation).items()
        }


@config.node
class SphericalTargettingCellTypes(
    CellTypeFilter, FractionFilter, Targetting, classmap_entry="sphere_cell_types"
):
    """
    Targets all cell types in a sphere.
    """

    origin: list[float] = config.attr(type=types.list(type=float, size=3), required=True)
    radius: float = config.attr(type=float, required=True)

    def _sphere_ids(self, ps):
        """
        The local ids of ``ps`` whose position falls within this targetting's sphere.
        """
        return ps.load_ids()[
            np.sum((ps.load_positions() - self.origin) ** 2, axis=1) < self.radius**2
        ]

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        """
        Target all or certain cells within a sphere of specified radius.
        """
        return {
            cell_name: self._sphere_ids(ps)
            for cell_name, ps in self._filtered_placement_sets(simulation).items()
        }

    @FractionFilter.filter
    def get_targets(self, adapter, simulation, simdata):
        """
        Target all or certain cells within a sphere of specified radius.

        Unlike the other targetting kinds, this one was never backed by a live
        population — its targets are placement ids, chunk-restricted the same way
        :class:`CellTypeFilter`'s are — so it keeps its own path here rather than
        going through :meth:`Targetting.get_targets`, which slices a backend
        population :attr:`get_placement_targets` never needed.
        """
        return {
            cell_name: self._sphere_ids(ps)
            for cell_name, ps in super().get_targets(adapter, simulation, simdata).items()
        }


@config.node
class SphericalTargetting(
    CellModelFilter, FractionFilter, CellTargetting, classmap_entry="sphere"
):
    """
    Targets all cells in a sphere.
    """

    origin: list[float] = config.attr(type=types.list(type=float, size=3), required=True)
    radius: float = config.attr(type=float, required=True)

    @FractionFilter.filter
    def get_placement_targets(self, simulation):
        """
        Target all or certain cells within a sphere of specified radius.
        """
        return {
            model: ids[
                (
                    np.sum(
                        (model.get_placement_set().load_positions() - self.origin) ** 2,
                        axis=1,
                    )
                    < self.radius**2
                )
            ]
            for model, ids in super().get_placement_targets(simulation).items()
        }


@config.dynamic(
    attr_name="strategy",
    default="everywhere",
    auto_classmap=True,
    classmap_entry="everywhere",
)
class LocationTargetting:
    def get_locations(self, cell):
        return [v for v in cell.locations.values()]


@config.node
class SomaTargetting(LocationTargetting, classmap_entry="soma"):
    def get_locations(self, cell):
        return [cell.locations[(0, 0)]]


@config.node
class LabelTargetting(LocationTargetting, classmap_entry="label"):
    labels = config.list(required=True)

    def get_locations(self, cell):
        locs = [
            loc
            for loc in cell.locations.values()
            if all(l_ in loc.section.labels for l_ in self.labels)
        ]
        return locs


@config.node
class BranchLocTargetting(LabelTargetting, classmap_entry="branch"):
    x = config.attr(type=types.fraction(), default=0.5)

    def get_locations(self, cell):
        locations = super().get_locations(cell)
        branches = set()
        selected = []
        for loc in locations:
            if (
                loc._loc[0] not in branches
                and loc.arc(0) <= self.x
                and loc.arc(1) > self.x
            ):
                selected.append(loc)
                branches.add(loc._loc[0])
        return selected


__all__ = [
    "BranchLocTargetting",
    "ByIdTargetting",
    "ByLabelTargetting",
    "CellModelFilter",
    "CellModelTargetting",
    "CellTargetting",
    "ConnectionTargetting",
    "CylindricalTargetting",
    "FractionFilter",
    "LabelTargetting",
    "LocationTargetting",
    "RepresentativesTargetting",
    "SomaTargetting",
    "SphericalTargetting",
    "Targetting",
]
