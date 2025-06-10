import typing
from collections import deque
from collections.abc import Iterable
from typing import Optional

import errr

from ._util import get_location_name
from .definitions import CableType, ModelDefinition
from .exceptions import ConstructionError, FrozenError, ModelDefinitionError

if typing.TYPE_CHECKING:
    from .parameter import Parameter

Location = tuple[int, int]
Interval = tuple[Location, Location]


def throw_frozen():
    raise FrozenError("Can't alter finished schematic.")


def _random_name():
    import random
    import string

    return "".join(random.choices(string.ascii_uppercase, k=10))


class Schematic:
    """
    A schematic is an intermediate object that associates parameter definitions to points
    in space. You can define locations (3d coords + radius) and tag them with labels, or
    set parameters directly on the locations. You can pass a schematic to a Builder, which
    will freeze the schematic (no changes can be made anymore) and create a simulator
    specific instance of the model.

    Schematics create a user-facing layer of "virtual branches", which is the network
    graph of the created locations. However, NEURON does not support the resolution that
    arbor does, so an underlying layer of "true branches" is created. In NEURON, a map is
    kept on the model between the locations on the virtual branches and the locations on
    the true branches, so that we can arbitrarily split up true branches into smaller
    pieces to achieve the resolution we need.
    """

    def __init__(self, name=None):
        self._name = name
        self._frozen = False
        self._definition: ModelDefinition = ModelDefinition()
        self.cables: list[CableBranch] = []
        self.roots: list[UnitBranch] = []
        self._named = 0

    def __iter__(self) -> typing.Iterator["UnitBranch"]:
        """
        Iterate over the unit branches depth-first order.
        """
        stack: deque[UnitBranch] = deque(self.roots)
        while True:
            try:
                branch = stack.pop()
            except IndexError:
                break
            yield branch
            if branch.children:
                stack.extend(reversed(branch.children))

    def __len__(self):
        return len([*iter(self)])

    @property
    def name(self):
        """
        Base name for all the instances of this model.

        Suffixed unique names for each
        instance can be obtained by calling ``create_name``.
        """
        return self._name

    @name.setter
    def name(self, value):
        if self._frozen:
            raise FrozenError("Can't change name of finished schematic.")
        else:
            self._name = value

    @property
    def definition(self):
        """
        Definition of the model, contains the definition of the parameters for the cables,
        mechanisms, and synapses of this model.
        """
        return self._definition.copy()

    @definition.setter
    def definition(self, value):
        if self._frozen:
            raise FrozenError("Can't change definitions of finished schematic.")
        else:
            self._definition = value

    def create_name(self):
        """
        Generate the next unique name for an instance of this model.
        """
        if not self._frozen:
            raise FrozenError("Schematic must be finished before naming instances of it.")
        self._named += 1
        return f"{self._name}_{self._named}"

    def create_location(
        self, location: tuple[int, int], coords, radii, labels, endpoint=None
    ):
        """
        Add a new location to the schematic. A location is a tuple of the branch id and
        point-on-branch id. Locations must be appended in ascending order.

        :param location:
        :param coords:
        :param radii:
        :param labels:
        :param endpoint:
        :return:
        """
        if self._frozen:
            throw_frozen()
        bid, pid = location
        next_bid = len(self.cables)
        if bid == next_bid:
            # We are starting a new branch
            branch = CableBranch()
            self.cables.append(branch)
        elif bid == next_bid - 1:
            # We are continuing the same branch
            branch = self.cables[bid]
        else:
            # Ascending branch order violated
            next_loc = f"({next_bid - 1}.{len(self.cables[next_bid - 1].points)})"
            raise ConstructionError(
                f"Locations need to be constructed in order. Can't construct "
                f"{location}, should construct {next_loc} or ({next_bid}.0)."
            )
        if pid != len(branch.points):
            # Ascending point order violated
            raise ConstructionError(
                f"Locations need to be constructed in order. Can't construct {location}"
                f", should construct ({bid}, {len(branch.points)}) or ({next_bid}.0)."
            )
        # We append the point to the cable, this may create new units.
        point = branch.append(location, coords, radii, labels)
        if endpoint:
            # If an endpoint was passed, we should set that as our parent both at the
            # cable and unit level.
            cable_parent = self.cables[endpoint[0]]
            unit_parent = cable_parent.points[endpoint[1]].branch
            # Set the child's parent cable
            branch.parent = cable_parent
            # Add the parent's child cable
            cable_parent.children.append(branch)
            # Set the child's parent unit
            point.branch.parent = unit_parent
            # Add the parent's child unit
            unit_parent.children.append(point.branch)
        elif pid == 0:
            # Otherwise, the first point of a branch without an endpoint should be added
            # to the roots of the schematic.
            self.roots.append(point.branch)

    def create_empty(self):
        """
        Create an empty branch.
        """
        if self._frozen:
            throw_frozen()
        self.cables.append(CableBranch())

    def set_param(self, location: Location | Interval | str, param: "Parameter"):
        if isinstance(location, str):
            # Set parameter for the global label definition
            self.definition[location].set(param)
        else:
            # Set parameter on the specific location or interval
            raise NotImplementedError(
                "Location or interval parameters not implemented yet."
            )

    def freeze(self):
        """
        Freeze the schematic.

        Most mutating operations will no longer be permitted.
        """
        if not self._frozen:
            self._flatten_branches(self.roots)
            self._name = self._name if self._name is not None else _random_name()
            self._frozen = True
            # If we are a constraint schematic, reconvert after freezing.
            if hasattr(self.definition, "convert_to_constraints"):
                self.definition.convert_to_constraints()
                # fixme: ion defaults are not constraints
                from .constraints import Constraint

                for branch in self:
                    for ion in branch.definition.ions.values():
                        for prop, value in ion:
                            setattr(ion, prop, Constraint.from_value(value))

    def _flatten_branches(self, branches: Iterable["UnitBranch"]):
        for branch in branches:
            # Concretize the true branch definition by merging all labels and params.
            branch.definition = self._makedef(branch.labels)
            try:
                # Assert that none of the values are missing (= `None`)
                branch.definition.assert_()
            except ValueError as e:
                locstr = get_location_name(branch.points)
                if not branch.labels:
                    raise ValueError(
                        f"Unlabeled {locstr} is missing value for {e.args[1]}."
                    ) from None
                raise ModelDefinitionError(
                    f"{locstr} labelled {errr.quotejoin(branch.labels)} "
                    f"misses value for {e.args[1:]}"
                ) from None
            self._flatten_branches(branch.children)

    def _makedef(self, labels: typing.Sequence[str]) -> CableType:
        # Determine the cable type priority order based on the key order in the dict.
        sort_labels = self._make_label_sorter()
        return self.definition.cable_type_class.anchor(
            (self._definition._cable_types.get(label) for label in sort_labels(labels)),
            synapses=self._definition.get_synapse_types(),
            use_defaults=self.definition.use_defaults,
            ion_class=self._definition.ion_class,
        )

    def get_cable_types(self):
        return self._definition.get_cable_types()

    def get_synapse_types(self):
        return self._definition.get_synapse_types()

    def get_compound_cable_types(self):
        if not self._frozen:
            raise RuntimeError("Can only compound cable types in frozen schematic.")

        name_labels = self._make_label_namer()
        return {name_labels(branch.labels): branch.definition for branch in self}

    def _make_label_sorter(self):
        insert_index = [*self._definition._cable_types.keys()].index

        def label_order(lbl):
            try:
                insert = insert_index(lbl)
            except ValueError:
                insert = -1
            return (insert, lbl)

        return lambda labels: sorted(labels, key=label_order)

    def _make_label_namer(self):
        sort_labels = self._make_label_sorter()
        return lambda labels: "_".join(
            label.replace("_", "__") for label in sort_labels(labels)
        )


class Point:
    def __init__(self, loc, branch: "UnitBranch", coords, radius):
        self.loc = loc
        self.coords = coords
        self.radius = radius
        self.branch = branch


class Branch:
    points: list[Point]
    parent: Optional["Branch"]
    children: list["Branch"]

    def __init__(self):
        self.points = []
        self.parent = None
        self.children = []


class CableBranch(Branch):
    parent: Optional["CableBranch"]
    children: list["CableBranch"]

    def append(self, loc, coords, radius, labels):
        if len(self.points):
            prev = self.points[-1]
            if prev.branch.labels == labels:
                # If we have the same labels, continue growing the true branch
                branch = prev.branch
            else:
                # If the labels change, create a new true branch
                branch = UnitBranch()
                branch.parent = prev.branch
                prev.branch.children.append(branch)
        else:
            branch = UnitBranch()
        branch.labels = labels.copy()
        point = Point(loc, branch, coords, radius)
        branch.points.append(point)
        self.points.append(point)
        return point


class UnitBranch(Branch):
    parent: Optional["UnitBranch"]
    children: list["UnitBranch"]
    labels: list[str]
    definition: CableType

    def append(self, point):
        self.points.append(point)
