import dataclasses
import typing
from collections import defaultdict
from itertools import tee
from math import isnan

if typing.TYPE_CHECKING:
    import arbor

    from .. import CableType
    from ..schematic import CableBranch, Point, Schematic


class CableCellTemplate:
    def __init__(
        self,
        morphology: "arbor.morphology",
        labels: "arbor.label_dict",
        decor: "arbor.decor",
    ):
        self.morphology = morphology
        self.labels = labels
        self.decor = decor

    def build(self):
        import arbor

        return arbor.cable_cell(self.morphology, self.decor, self.labels)


def hash_labelset(labels: list[str]):
    return "&".join(label.replace("&", "&&") for label in sorted(labels))


def get_label_dict(schematic: "Schematic"):
    import arbor

    labelsets: dict[str, int] = {}
    label_dict = defaultdict(list)
    for b in schematic.cables:
        for p in b.points:
            h = hash_labelset(p.branch.labels)
            if h not in labelsets:
                lset_id = len(labelsets)
                for label in p.branch.labels:
                    label_dict[label].append(lset_id)
                labelsets[h] = lset_id
    return labelsets, arbor.label_dict(
        {
            label: (
                "(join " + " ".join(f"(tag {tag})" for tag in tags) + ")"
                if len(tags) > 1
                else f"(tag {tags[0]})"
            )
            for label, tags in label_dict.items()
        }
    )


def _to_units(value, unit: "arbor.units.unit") -> "arbor.units.quantity":
    import arbor

    # todo: drop when units are released
    if hasattr(arbor, "units") and isinstance(value, arbor.units.quantity):
        ret = value.value_as(unit)
        if isnan(ret):
            raise ValueError(f"Can't convert {value.units} to {unit}.")
        return ret * unit
    else:
        return value * unit


def paint_cable_type_cable(decor: "arbor.decor", label: str, cable_type: "CableType"):
    import arbor

    decor.paint(
        f'"{label}"',
        cm=_to_units(
            cable_type.cable.cm,
            (arbor.units.F / arbor.units.m2) if hasattr(arbor, "units") else 1,
        ),
        rL=_to_units(
            cable_type.cable.Ra,
            (arbor.units.Ohm * arbor.units.cm) if hasattr(arbor, "units") else 1,
        ),
    )


def paint_cable_type_ions(decor: "arbor.decor", label: str, cable_type: "CableType"):
    import arbor

    units = (
        {
            "rev_pot": arbor.units.mV,
            "int_con": arbor.units.mM,
            "ext_con": arbor.units.mM,
        }
        if hasattr(arbor, "units")
        # todo: drop when units are released
        else defaultdict(lambda: 1)
    )
    for ion_name, ion in cable_type.ions.items():
        try:
            decor.paint(
                f'"{label}"',
                ion=ion_name,
                **{k: _to_units(v, units[k]) for k, v in dataclasses.asdict(ion).items()},
            )
        except TypeError:
            # todo: drop when units are released
            # Support older `ion_name` kwarg
            decor.paint(
                f'"{label}"',
                ion_name=ion_name,
                **{k: _to_units(v, units[k]) for k, v in dataclasses.asdict(ion).items()},
            )


def paint_cable_type_mechanisms(
    decor: "arbor.decor", label: str, cable_type: "CableType"
):
    import arbor

    for mech_id, mech in cable_type.mechs.items():
        decor.paint(f'"{label}"', arbor.density(mech_id, mech.parameters))


def paint_cable_type(decor: "arbor.decor", label: str, cable_type: "CableType"):
    paint_cable_type_cable(decor, label, cable_type)
    paint_cable_type_ions(decor, label, cable_type)
    paint_cable_type_mechanisms(decor, label, cable_type)


def get_decor(schematic: "Schematic"):
    import arbor

    decor = arbor.decor()
    for label, cable_type in schematic.definition.get_cable_types().items():
        paint_cable_type(decor, label, cable_type)

    return decor


def arbor_build(schematic: "Schematic"):
    import arbor

    schematic.freeze()
    if not hasattr(schematic, "arbor"):
        tree = arbor.segment_tree()
        # Stores the ids of the segments to append to.
        branch_endpoints: dict[CableBranch, int] = {}
        labelsets, label_dict = get_label_dict(schematic)
        for bid, branch in enumerate(schematic.cables):
            if len(branch.points) < 2:
                # Empty branches mess up the branch id numbering, so we forbid them
                raise RuntimeError(f"Branch {bid} needs at least 2 points.")
            pts = iter(branch.points)
            # Set up pairwise iterators
            pts_a, pts_b = tee(pts)
            next(pts_b)
            # Start branch from the endpoint, if the branch has a parent.
            ptid = branch_endpoints[branch.parent] if branch.parent else arbor.mnpos
            for _, (p1, p2) in enumerate(zip(pts_a, pts_b, strict=False)):
                # Tag it with a unique tag per label combination
                tag = hash_labelset(p2.branch.labels)
                ptid = tree.append(ptid, _mkpt(p1), _mkpt(p2), tag=labelsets.get(tag))
            branch_endpoints[branch] = ptid

        schematic.arbor = CableCellTemplate(
            arbor.morphology(tree),
            label_dict,
            get_decor(schematic),
        )
    return schematic.arbor.build()


def _mkpt(p: "Point") -> "arbor.mpoint":
    import arbor

    return arbor.mpoint(*p.coords, p.radius)
