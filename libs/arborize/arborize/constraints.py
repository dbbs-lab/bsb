import dataclasses
import itertools
import typing

from ._util import MechId
from .definitions import (
    CableProperties,
    CableType,
    Definition,
    Ion,
    Mechanism,
    Synapse,
    _parse_dict_def,
)


class Constraint:
    def __init__(self):
        self._upper = None
        self._lower = None
        self._tolerance = None

    @property
    def tolerance(self):
        return self._tolerance

    @property
    def lower(self):
        value = self._lower
        if self.tolerance is not None:
            value *= 1 - self.tolerance
        return value

    @lower.setter
    def lower(self, value: float):
        self._lower = value

    @property
    def upper(self):
        value = self._upper
        if self.tolerance is not None:
            value *= 1 - self.tolerance
        return value

    @upper.setter
    def upper(self, value: float):
        self._upper = value

    @classmethod
    def from_value(cls, value: "ConstraintValue") -> "Constraint":
        if isinstance(value, Constraint):
            return value
        elif isinstance(value, (list, tuple)):
            constraint = cls()
            constraint.lower = value[0]
            constraint.upper = value[1]
        else:
            constraint = cls()
            constraint.upper = value
            constraint.lower = value
        return constraint

    def set_tolerance(self, tolerance=None):
        self._tolerance = tolerance
        return self


ConstraintValue = typing.Union[Constraint, float, tuple[float, float], list[float]]


@dataclasses.dataclass
class CablePropertyConstraints(CableProperties):
    Ra: Constraint
    """
    Axial resistivity in ohm/cm
    """
    cm: Constraint
    """
    Membrane conductance
    """

    def __post_init__(self):
        for field in dataclasses.fields(self):
            _convert_field(self, field)


CablePropertyConstraintsDict = typing.TypedDict(
    "CablePropertyConstraintsDict",
    {"Ra": ConstraintValue, "cm": ConstraintValue},
    total=False,
)


@dataclasses.dataclass
class IonConstraints(Ion):
    rev_pot: Constraint
    int_con: Constraint
    ext_con: Constraint

    def __post_init__(self):
        for field in dataclasses.fields(self):
            _convert_field(self, field)


IonConstraintsDict = typing.TypedDict(
    "IonConstraintsDict",
    {
        "rev_pot": ConstraintValue,
        "int_con": ConstraintValue,
        "ext_con": ConstraintValue,
    },
    total=False,
)


class MechanismConstraints(Mechanism):
    parameters: dict[str, Constraint]

    def __init__(self, parameters: dict[str, ConstraintValue]):
        super().__init__({k: Constraint.from_value(v) for k, v in parameters.items()})


class SynapseConstraints(Synapse, MechanismConstraints):
    pass


SynapseConstraintsDict = typing.Union[
    dict[str, ConstraintValue],
    typing.TypedDict(
        "SynapseConstraintsDict",
        {"mechanism": MechId, "parameters": dict[str, ConstraintValue]},
        total=False,
    ),
]


class CableTypeConstraints(CableType):
    cable: CablePropertyConstraints
    mechs: dict[MechId, MechanismConstraints]
    ions: dict[str, IonConstraints]
    synapses: dict[str, SynapseConstraints]

    @classmethod
    def default(cls, ion_class=IonConstraints):
        default = super().default(ion_class=ion_class)
        for field in dataclasses.fields(default.cable):
            setattr(
                default.cable,
                field.name,
                Constraint.from_value(getattr(default.cable, field.name)),
            )
        return default


CableTypeConstraintsDict = typing.TypedDict(
    "CableTypeConstraintsDict",
    {
        "cable": CablePropertyConstraintsDict,
        "mechanisms": dict[MechId, dict[str, ConstraintValue]],
        "ions": dict[str, IonConstraintsDict],
        "synapses": dict[str, SynapseConstraintsDict],
    },
    total=False,
)


class ConstraintsDefinition(
    Definition[
        CableTypeConstraints,
        CablePropertyConstraints,
        IonConstraints,
        MechanismConstraints,
        SynapseConstraints,
    ]
):
    @classmethod
    @property
    def cable_type_class(cls):
        return CableTypeConstraints

    @classmethod
    @property
    def cable_properties_class(cls):
        return CablePropertyConstraints

    @classmethod
    @property
    def ion_class(cls):
        return IonConstraints

    @classmethod
    @property
    def mechanism_class(cls):
        return MechanismConstraints

    @classmethod
    @property
    def synapse_class(cls):
        return SynapseConstraints

    def set_tolerance(self, tolerance=None):
        for syn in self._synapse_types.values():
            for p in syn.parameters.values():
                p.set_tolerance(tolerance)

        for ct in self._cable_types.values():
            for field in dataclasses.fields(ct.cable):
                getattr(ct.cable, field.name).set_tolerance(tolerance)
            for ion in ct.ions.values():
                for field in dataclasses.fields(ion):
                    getattr(ion, field.name).set_tolerance(tolerance)
            for mech in itertools.chain(ct.mechs.values(), ct.synapses.values()):
                for p in mech.parameters.values():
                    p.set_tolerance(tolerance)


def _convert_field(obj, field):
    constraint = Constraint.from_value(getattr(obj, field.name))
    setattr(obj, field.name, constraint)


ConstraintsDefinitionDict = typing.TypedDict(
    "ConstraintsDefinitionDict",
    {
        "cable_types": dict[str, CableTypeConstraintsDict],
        "synapse_types": dict[MechId, SynapseConstraintsDict],
    },
    total=False,
)


def define_constraints(
    constraints: ConstraintsDefinitionDict, tolerance=None, use_defaults=False
) -> ConstraintsDefinition:
    constraints = _parse_dict_def(ConstraintsDefinition, constraints)
    constraints.set_tolerance(tolerance)
    constraints.use_defaults = use_defaults
    return constraints
