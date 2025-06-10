import os
import re
import typing
from collections import defaultdict

from ..constraints import Constraint, ConstraintsDefinition
from ._neuron import neuron_build

if typing.TYPE_CHECKING:
    from ..schematic import Schematic


def bluepyopt_build(schematic: "Schematic"):
    import bluepyopt.ephys as ephys
    import glia

    if os.getenv("ARBORIZE_DILL", True):
        import multiprocessing

        import dill

        dill.Pickler.dumps, dill.Pickler.loads = dill.dumps, dill.loads
        multiprocessing.reduction.ForkingPickler = dill.Pickler
        multiprocessing.reduction.dump = dill.dump

    class ArborizeMorphology(ephys.morphologies.Morphology):
        def __init__(self, schematic: "Schematic"):
            super().__init__()
            self._schematic = schematic

        def instantiate(self, sim=None, icell=None):
            self.arborized_cell = neuron_build(self._schematic)
            for label in self._schematic.get_compound_cable_types():
                section_list = getattr(icell, label)
                labels = [
                    label.replace("__", "_") for label in re.split("(?<!_)_(?!_)", label)
                ]
                for sec in self.arborized_cell.get_sections_with_all_labels(labels):
                    section_list.append(sec.__neuron__())

        def destroy(self, sim=None):
            del self.arborized_cell

    morph = ArborizeMorphology(schematic)
    schematic.freeze()
    constraints = schematic.definition
    if not isinstance(constraints, ConstraintsDefinition):
        raise TypeError(
            "Optimization schematic must contain constraints"
            f", got {type(constraints)} instead."
        )
    cable_types = schematic.get_compound_cable_types()

    bpyopt_seclists = {
        label: ephys.locations.NrnSeclistLocation(label, seclist_name=label)
        for label in cable_types
    }

    mech_locations = defaultdict(list)
    for label, cable_type in cable_types.items():
        for mech in cable_type.mechs:
            mech_locations[mech].append(bpyopt_seclists[label])

    bpyopt_mechs = [
        ephys.mechanisms.NrnMODMechanism(
            name=glia.resolve(mech), prefix=glia.resolve(mech), locations=locations
        )
        for mech, locations in mech_locations.items()
    ]

    bpyopt_cable_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{label}_{prop}",
            param_name=prop,
            locations=[bpyopt_seclists[label]],
            **_to_bpyopt_kwargs(constraint),
        )
        for label, cable_type in cable_types.items()
        for prop, constraint in cable_type.cable
    ]

    ion_prop_map = {"rev_pot": "e{ion}", "int_con": "{ion}i", "ext_con": "{ion}o"}
    bpyopt_ion_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{label}_{ion}_{prop}",
            param_name=ion_prop_map[prop].format(ion=ion_name),
            locations=[bpyopt_seclists[label]],
            **_to_bpyopt_kwargs(constraint),
        )
        for label, cable_type in cable_types.items()
        for ion_name, ion in cable_type.ions.items()
        for prop, constraint in ion
    ]

    bpyopt_mech_params = [
        ephys.parameters.NrnSectionParameter(
            name=f"{param}_{glia.resolve(mech_id)}_{label}",
            param_name=f"{param}_{glia.resolve(mech_id)}",
            locations=[bpyopt_seclists[label]],
            **_to_bpyopt_kwargs(constraint),
        )
        for label, cable_type in cable_types.items()
        for mech_id, mech in cable_type.mechs.items()
        for param, constraint in mech.parameters.items()
    ]

    bpyopt_params = [
        ephys.parameters.NrnGlobalParameter(
            "temperature", param_name="celsius", value=32, frozen=True
        ),
        *bpyopt_mech_params,
        *bpyopt_cable_params,
        *bpyopt_ion_params,
    ]

    return ephys.models.CellModel(
        schematic.create_name(),
        morph,
        bpyopt_mechs,
        bpyopt_params,
        secarray_names=[],
        seclist_names=[*bpyopt_seclists.keys()],
    )


def _to_bpyopt_kwargs(constraint: "Constraint"):
    frozen = constraint.upper == constraint.lower
    return dict(
        frozen=frozen,
        bounds=[constraint.lower, constraint.upper] if not frozen else None,
        value=constraint.upper if frozen else None,
    )
