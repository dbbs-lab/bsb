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
        elif isinstance(value, list | tuple):
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


ConstraintValue = Constraint | float | tuple[float, float] | list[float]
"""
Type alias for values used to specify constraints.

Can be:
- A single :class:`Constraint` instance,
- A single float value,
- A tuple of two floats representing a range (lower, upper),
- A list of floats representing a range (lower, upper).

This flexible type allows defining constraints either as explicit
`Constraint` objects or as simple numeric bounds.
"""


@dataclasses.dataclass
class CablePropertyConstraints(CableProperties):
    Ra: Constraint
    """
    Axial resistivity in ohm/cm.
    """
    cm: Constraint
    """
    Membrane conductance.
    """

    def __post_init__(self):
        for field in dataclasses.fields(self):
            _convert_field(self, field)


class CablePropertyConstraintsDict(typing.TypedDict, total=False):
    Ra: ConstraintValue
    cm: ConstraintValue


@dataclasses.dataclass
class IonConstraints(Ion):
    rev_pot: Constraint
    int_con: Constraint
    ext_con: Constraint

    def __post_init__(self):
        for field in dataclasses.fields(self):
            _convert_field(self, field)


class IonConstraintsDict(typing.TypedDict, total=False):
    rev_pot: ConstraintValue
    int_con: ConstraintValue
    ext_con: ConstraintValue


class MechanismConstraints(Mechanism):
    parameters: dict[str, Constraint]

    def __init__(self, parameters: dict[str, ConstraintValue]):
        super().__init__({k: Constraint.from_value(v) for k, v in parameters.items()})


class SynapseConstraints(Synapse, MechanismConstraints):
    pass


SynapseConstraintsDict = dict[str, ConstraintValue] | typing.TypedDict(
    "SynapseConstraintsDict",
    {"mechanism": MechId, "parameters": dict[str, ConstraintValue]},
    total=False,
)
"""
Type definition for synapse constraints.

This can be either:

- A dictionary mapping parameter names to :data:`ConstraintValues <ConstraintValue>`, or
- A TypedDict with optional keys:

  - ``mechanism``: Identifier for the synapse mechanism (type
     :class:`~arborize._util.MechId`).
   
  - ``parameters``: Dictionary of parameter names to 
     :data:`ConstraintValues <ConstraintValue>`.

This flexible type supports simple parameter dicts or more structured dicts
including the synapse mechanism identifier.
"""


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


class CableTypeConstraintsDict(typing.TypedDict, total=False):
    cable: CablePropertyConstraintsDict
    mechanisms: dict[MechId, dict[str, ConstraintValue]]
    ions: dict[str, IonConstraintsDict]
    synapses: dict[str, SynapseConstraintsDict]


"""
Typed dictionary representing constraints for a cable type.

Fields:

- ``cable``: Dictionary of cable property constraints (e.g., Ra, cm).
- ``mechanisms``: Mapping from mechanism IDs to their parameter constraints.
- ``ions``: Mapping from ion names to their ion-specific constraints.
- ``synapses``: Mapping from synapse names to their synapse-specific constraints.

All fields are optional.
"""


class ConstraintsDefinition(
    Definition[
        CableTypeConstraints,
        CablePropertyConstraints,
        IonConstraints,
        MechanismConstraints,
        SynapseConstraints,
    ]
):
    """
    A specialized Definition that supports parameter constraints for cable types, ions,
    mechanisms, and synapses.

    This class wraps all components with `Constraint` instances, allowing ranges or
    tolerances to be applied to physiological parameters. Use `define_constraints` to
    create an instance from a dictionary and apply a global tolerance.

    Example::

        constraints = define_constraints(
            {
                "cable_types": {
                    "dend": {
                        "cable": {"Ra": (100, 200), "cm": 1.0},
                        "ions": {
                            "na": {
                                "rev_pot": -65.0,
                                "int_con": (10.0, 15.0),
                                "ext_con": 150.0,
                            },
                        },
                        "mechanisms": {"hh": {"gnabar": (0.1, 0.3), "gl": 0.0003}},
                    }
                }
            },
            tolerance=0.1,
        )

    :ivar cable_type_class: The class used for representing constrained cable types.
    :vartype cable_type_class: type[CableTypeConstraints]
    :ivar cable_properties_class: The class used for constrained cable properties
     (e.g., Ra, cm).
    :vartype cable_properties_class: type[CablePropertyConstraints]
    :ivar ion_class: The class used for constrained ion properties.
    :vartype ion_class: type[IonConstraints]
    :ivar mechanism_class: The class used for constrained mechanism parameters.
    :vartype mechanism_class: type[MechanismConstraints]
    :ivar synapse_class: The class used for constrained synapse parameters.
    :vartype synapse_class: type[SynapseConstraints]

    :param tolerance: Optional tolerance to apply to all parameter constraints
     (e.g., 0.1 = ±10%).
    :type tolerance: float or None

    :return: A fully structured `ConstraintsDefinition` with all values wrapped in
     `Constraint` objects.
    :rtype: ConstraintsDefinition
    """

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


class ConstraintsDefinitionDict(typing.TypedDict, total=False):
    cable_types: dict[str, CableTypeConstraintsDict]
    synapse_types: dict[MechId, SynapseConstraintsDict]


"""
Typed dictionary for the overall constraints definition structure.

Fields:

- ``cable_types``: A dictionary mapping cable type names to their constraint dictionaries.
- ``synapse_types``: A dictionary mapping mechanism ID to synapse constraint dictionaries.

Both fields are optional and represent the hierarchical constraint configuration
used to build a `ConstraintsDefinition` instance.
"""


def define_constraints(
    constraints: ConstraintsDefinitionDict, tolerance=None, use_defaults=False
) -> ConstraintsDefinition:
    """
    Create a `ConstraintsDefinition` instance from a dictionary of constraints, applying
    an optional global tolerance and default values.

    :param constraints: Dictionary specifying constraint values structured as
                        `ConstraintsDefinitionDict`.
    :type constraints: ConstraintsDefinitionDict
    :param tolerance: Optional tolerance to apply to all parameter constraints
                      (e.g., 0.1 means ±10%), defaults to None.
    :type tolerance: float or None
    :param use_defaults: Whether to fill in missing constraint values with defaults,
                         defaults to False.
    :type use_defaults: bool

    :return: A fully constructed `ConstraintsDefinition` instance with all values
             wrapped in `Constraint` objects and tolerance applied.
    :rtype: ConstraintsDefinition
    """
    constraints = _parse_dict_def(ConstraintsDefinition, constraints)
    constraints.set_tolerance(tolerance)
    constraints.use_defaults = use_defaults
    return constraints
