import dataclasses
import random
import typing
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

import errr

from .._util import get_arclengths, get_location_name
from ..constraints import Constraint
from ..definitions import CableProperties, Ion, Mechanism, MechId, mechdict
from ..exceptions import TransmitterError, UnknownLocationError, UnknownSynapseError

if TYPE_CHECKING:
    from glia._glia import MechAccessor
    from patch.objects import PointProcess, Section, Segment

    from ..schematic import Location, Schematic


class NeuronModel:
    def __init__(self, sections, locations, cable_types):
        self._sections: Sequence[Section] = sections
        self._locations: dict[Location, LocationAccessor] = locations
        self._cable_types = cable_types

    @property
    def sections(self) -> Sequence["Section"]:
        return self._sections

    @property
    def locations(self) -> Mapping["Location", "LocationAccessor"]:
        return self._locations

    def get_location(self, loc: "Location") -> "LocationAccessor":
        try:
            return self._locations[tuple(loc)]
        except KeyError:
            raise UnknownLocationError(
                "No such location '%location%'.", self, loc
            ) from None

    def get_segment(self, loc: "Location", sx=0.5) -> "Segment":
        la = self.get_location(loc)
        return la.section(la.arc(sx))

    def get_sections_with_label(self, label: str):
        return [s for s in self.sections if label in s.labels]

    def get_sections_with_any_label(self, labels: list[str]):
        return [s for s in self.sections if any(lbl in labels for lbl in s.labels)]

    def get_sections_with_all_labels(self, labels: list[str]):
        return [s for s in self.sections if all(lbl in labels for lbl in s.labels)]

    def insert_synapse(
        self,
        label: typing.Union[str, "MechId"],
        loc: "Location",
        attributes=None,
        sx=0.5,
    ) -> "PointProcess":
        import glia

        la = self.get_location(loc)
        synapses = la.section.synapse_types
        if not synapses:
            raise UnknownSynapseError(
                "Can't insert synapses. No synapse types present on branch with labels "
                + errr.quotejoin(la.section.labels),
                self,
                label,
            )
        try:
            synapse = synapses[label]
        except KeyError:
            raise UnknownSynapseError(
                f"Synapse type '%synapse%' not present on branch with labels "
                f"{errr.quotejoin(la.section.labels)}. Choose from: "
                f"{errr.quotejoin(synapses)}",
                self,
                label,
            ) from None
        mech = glia.insert(la.section, *synapse.mech_id, x=la.arc(sx))
        mech.set(synapse.parameters)
        mech.synapse_name = label
        la.section.synapses.append(mech)

        return mech

    def insert_receiver(
        self,
        gid: int,
        label: typing.Union[str, "MechId"],
        loc: "Location",
        attributes=None,
        sx=0.5,
        source=None,
        **kwargs,
    ):
        from patch import p

        synapse = self.insert_synapse(label, loc, attributes, sx)
        synapse.gid = gid
        if source is None:
            return p.ParallelCon(gid, synapse, **kwargs)
        else:
            spp = synapse._point_process
            p.parallel.target_var(spp, getattr(spp, "_ref_" + source), gid)

    def insert_transmitter(
        self, gid: int, loc: "Location", sx=0.5, source=None, **kwargs
    ):
        from patch import p

        la = self.get_location(loc)
        if source is None:
            if hasattr(la.section, "_transmitter"):
                if gid != la.section._transmitter.gid:
                    raise TransmitterError(
                        "A transmitter already exists"
                        f" with gid {la.section._transmitter.gid}"
                    )
                return la.section._transmitter
            else:
                tm = p.ParallelCon(self.get_segment(loc, sx), gid, **kwargs)
                la.section._transmitter = tm
        else:
            if hasattr(la.section, "_source"):
                if gid != la.section._source_gid:
                    raise TransmitterError(
                        "A source variable already exists"
                        f" with gid {la.section._source_gid}"
                    )
                tm = la.section._source
            else:
                source_var = self.get_segment(loc, sx)._ref_v
                tm = p.parallel.source_var(source_var, gid, sec=la.section.__neuron__())
                la.section._source = source_var
                la.section._source_gid = gid
        return tm

    def get_random_location(self):
        return random.choice([*self._locations.keys()])

    def record(self):
        soma = [s for s in self._sections if "soma" in s.labels]
        if not soma:
            raise RuntimeError("No soma to record from")
        else:
            return soma[0].record()

    def __getattr__(self, item):
        if item in self._cable_types:
            return [s for s in self._sections if item in s.labels]
        else:
            return super().__getattribute__(item)


def neuron_build(schematic: "Schematic"):
    schematic.freeze()
    name = schematic.create_name()
    branchmap = {}
    sections = []
    locations = {}
    for branch in schematic:
        bname = f"{name}_{get_location_name(branch.points)}"
        alens = get_arclengths(branch.points)
        section, mechs = _build_branch(branch, bname)
        section.locations = [point.loc for point in branch.points]
        for i, point in enumerate(branch.points):
            try:
                arcpair = (alens[i], alens[i + 1])
            except IndexError:
                arcpair = (1, 1)
            locations[point.loc] = LocationAccessor(point.loc, section, mechs, arcpair)
        sections.append(section)
        branchmap[branch] = section
        if branch.parent:
            section.connect(branchmap[branch.parent])
    return NeuronModel(sections, locations, [*schematic.get_cable_types().keys()])


def _build_branch(branch, name):
    from patch import p

    section = p.Section(name=name)
    section.labels = [*branch.labels]
    section.synapses = []
    apply_geometry(section, branch.points)
    apply_cable_properties(section, branch.definition.cable)
    mechs = apply_mech_definitions(section, branch.definition.mechs)
    apply_ions(section, branch.definition.ions)
    section.synapse_types = branch.definition.synapses
    return section, mechs


def apply_geometry(section, points):
    coords = []
    diams = []
    for point in points:
        coords.append(point.coords)
        diams.append(point.radius * 2)
    section.add_3d(coords, diams)
    section.nseg = int((section.L // 10) + 1)


def apply_cable_properties(section, cable_props: "CableProperties"):
    for field in dataclasses.fields(cable_props):
        prop = getattr(cable_props, field.name)
        if not isinstance(prop, Constraint):
            setattr(section, field.name, prop)


def apply_ions(section, ions: dict[str, "Ion"]):
    prop_map = {"rev_pot": "e{ion}", "int_con": "{ion}i", "ext_con": "{ion}o"}
    for ion_name, ion_props in ions.items():
        for prop, value in ion_props:
            if not isinstance(value, Constraint):
                setattr(
                    section,
                    prop_map[prop].format(ion=ion_name),
                    value,
                )


def apply_mech_definitions(section, mech_defs: dict["MechId", "Mechanism"]):
    import glia

    mechs = {}
    for mech_id, mech_def in mech_defs.items():
        if isinstance(mech_id, str):
            mech_id = (mech_id,)
        mech = glia.insert(section, *mech_id)
        for param_name, param_value in mech_def.parameters.items():
            if not isinstance(param_value, Constraint):
                mech.set_parameter(param_name, param_value)
        mechs[mech_id] = mech

    return mechs


class LocationAccessor:
    def __init__(self, loc, section, mechs, arcs):
        self._loc = loc
        self._section = section
        self._mechs = mechdict(mechs)
        self._arcs = arcs

    def set_parameter(self, *args, **kwargs):
        """
        Not implemented yet.
        """
        raise NotImplementedError(
            "Parameters cannot be changed yet after cell construction."
        )

    @property
    def section(self):
        return self._section

    @property
    def mechanisms(self) -> Mapping["MechId", "MechAccessor"]:
        return self._mechs

    def arc(self, x=0):
        a0, a1 = self._arcs
        return (a1 - a0) * x + a0
