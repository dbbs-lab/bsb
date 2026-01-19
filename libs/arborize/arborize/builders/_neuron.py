import dataclasses
import random
import typing
import warnings
from collections import deque
from collections.abc import Mapping, Sequence

import errr

from .._util import get_arclengths, get_location_name
from ..constraints import Constraint
from ..definitions import CableProperties, Ion, Mechanism, MechId, mechdict
from ..exceptions import (
    TransmitterError,
    UnconnectedPointInSpaceWarning,
    UnknownLocationError,
    UnknownSynapseError,
)

if typing.TYPE_CHECKING:  # pragma: nocover
    from glia._glia import MechAccessor
    from patch.objects import PointProcess, Section, Segment

    from ..schematic import Location, Schematic, UnitBranch


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
        arc = la.arc(sx)
        # The start (0) and end (1) of a Section are special 0 area nodes
        # that may be shared with sibling or child Section respectively.
        # It's not safe to use these in a parallel context, see
        # https://github.com/dbbs-lab/bsb/issues/159
        if arc == 0:
            arc = 0.0001
        if arc == 1:
            arc = 0.9999
        return la.section(arc)

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
            spp = synapse._pp
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
                seg = self.get_segment(loc, sx)
                tm = p.ParallelCon(seg, gid, **kwargs)
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
    branch_map = {}
    sections = []
    proxies = []
    locations = {}
    for branch in schematic:
        branch_name = f"{name}_{get_location_name(branch.points)}"
        arc_lengths = get_arclengths(branch.points)
        section, mechanisms = _build_branch_or_proxy(branch, branch_name)
        if not isinstance(section, _SinglePointProxy):
            # We're dealing with a real section!
            # Store the points on the section for later use.
            section.locations = [point.loc for point in branch.points]
            # Create a location accessor for each point
            for i, point in enumerate(branch.points):
                try:
                    arc_pair = (arc_lengths[i], arc_lengths[i + 1])
                except IndexError:
                    arc_pair = (1, 1)
                # Store the location accessor on the locations lookup map
                locations[point.loc] = LocationAccessor(
                    point.loc, section, mechanisms, arc_pair
                )
            # Store the section in the sections list
            sections.append(section)
            # Store it in the branch map so its children can find their parent
            branch_map[branch] = section
            # If it has a parent, look it up in the branch map and connect it
            if branch.parent:
                # This function makes it safe to connect to proxies
                _connect_section_or_proxy(section, branch_map[branch.parent])
        else:
            # We're dealing with a single point proxy
            proxies.append(section)
            branch_map[branch] = section
            # Connect the proxy to its parent
            _connect_section_or_proxy(section, branch_map.get(branch.parent))

    _collapse_proxies(proxies)

    return NeuronModel(sections, locations, [*schematic.get_cable_types().keys()])


class _SinglePointProxy:
    def __init__(self, branch: "UnitBranch", branch_name: str):
        self.children = []
        self.branch = branch
        self.branch_name = branch_name
        self.parent = None
        self.reified = False


def _build_branch_or_proxy(branch: "UnitBranch", name: str):
    from patch import p

    if len(branch.points) < 2:
        return _SinglePointProxy(branch, name), []

    section = p.Section(name=name)
    section.labels = [*branch.labels]
    section.synapses = []
    apply_geometry(section, branch.points)
    apply_cable_properties(section, branch.definition.cable)
    mechanisms = apply_mech_definitions(section, branch.definition.mechs)
    apply_ions(section, branch.definition.ions)
    section.synapse_types = branch.definition.synapses
    return section, mechanisms


def _connect_section_or_proxy(section, parent):
    connect = True
    if isinstance(section, _SinglePointProxy):
        section.parent = parent
        connect = False
    if isinstance(parent, _SinglePointProxy):
        parent.children.append(section)
        connect = False
    if connect:
        section.connect(parent)


def _collapse_proxies(proxies: list[_SinglePointProxy]):
    """
    Removes proxies from the schematic and connects the real sections to each
    other.

    Nota bene: Locations are added to schematics in an ordered incremental
    fashion from branch 0 to branch N with higher branch numbers always being
    later siblings or children of lower branch numbers. Since `neuron_build`
    iterates over the branches in insert order and adds proxies to the list
    during that iteration, proxies will also occur in this list in the same
    order where parents appear before their children.

    That means that a proxy that has another proxy as a parent has already
    been collapsed as a direct child of the parent proxy in a previous
    iteration and can be skipped.
    """

    for proxy in proxies:
        if proxy.reified:
            # This proxy has already been reified/collapsed in a previous
            # iteration as a downstream of another proxy.
            continue
        if not proxy.parent:
            # Root proxies
            if len(proxy.children) == 0:
                # Root proxy without children, no connections need to be made,
                # the proxy can simply be ignored.
                if len(proxy.branch.points) > 0:
                    # Floating point in space somewhere, not supported by
                    # NEURON. Warn the user as this is probably not intentional.
                    warnings.warn(
                        f"Branch '{proxy.branch_name}' has a single "
                        f"point {proxy.branch.points[0].loc} in space at "
                        f"{proxy.branch.points[0].coords} not connected to "
                        "anything. This is not supported by NEURON and will be "
                        "ignored.",
                        UnconnectedPointInSpaceWarning,
                        stacklevel=2,
                    )
                continue
            else:
                # Root proxy with child(ren), connect them to the start of
                # the first child.

                # The children might be proxies themselves, so we need to
                # reify them to a collection of actual sections they
                # eventually point to.
                true_children = _reify_proxy_children(proxy)

                first_child = true_children[0]
                # We loop only over *additional* children, so that this
                # algorithm does nothing in the case of a single child
                # connected to a single point root proxy, where the root
                # proxy point can simply be discarded.
                for child in true_children[1:]:
                    child.connect(first_child, 0)
        else:
            # Proxies with a parent, connect the proxy children to the parent.

            # The parent should never be a proxy itself (see docstring),
            # error if it is.
            if isinstance(proxy.parent, _SinglePointProxy):  # pragma: nocover
                raise RuntimeError(
                    f"Parent of proxy {proxy.branch_name} is a proxy itself."
                    " Please report this bug."
                )

            # The children might be proxies themselves, so we reify them.
            true_children = _reify_proxy_children(proxy)

            for child in true_children:
                _connect_section_or_proxy(child, proxy.parent)


def _reify_proxy_children(proxy):
    stack = deque(reversed(proxy.children))
    true_children = []

    while True:
        try:
            child = stack.pop()
        except IndexError:
            break
        if isinstance(child, _SinglePointProxy):
            child.reified = True
            if child.children:
                stack.extend(reversed(child.children))
        else:
            true_children.append(child)

    return true_children


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
