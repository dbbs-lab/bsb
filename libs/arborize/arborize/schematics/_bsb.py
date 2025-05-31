import itertools
from typing import TYPE_CHECKING, Optional

from ..schematic import Schematic

if TYPE_CHECKING:
    import bsb.morphologies

    from ..definitions import Definition


def bsb_schematic(
    morphology: "bsb.morphologies.Morphology",
    definitions: Optional["Definition"] = None,
) -> Schematic:
    """
    Generate a schematic from a bsb.Morphology object.

    :param morphology: A bsb.Morphology instance.
    :type morphology: bsb.morphologies.Morphology
    :param definitions: Optional Definition instance.
    :type definitions: arborize.definitions.Definition
    :return: A schematic representation.
    :rtype: arborize.schematic.Schematic
    """
    schematic = Schematic(name=morphology.meta.get("name"))
    branches: list[bsb.morphologies.Branch] = [*morphology.branches]
    endpoints = []
    for bid, branch in enumerate(branches):
        branch._tempid = bid
        if not len(branch):
            true_parent = None
            while True:
                parent = branch.parent
                if parent is None:
                    break
                elif len(parent):
                    true_parent = endpoints[parent._tempid]
                    break
            schematic.create_empty()
            endpoints.append(true_parent)
        else:
            if branch.parent is not None:
                endpoint = endpoints[branch.parent._tempid]
            else:
                endpoint = None
            for pid, coords, radius, labels in zip(
                itertools.count(), branch.points, branch.radii, branch.labels.walk()
            ):
                endpoint = endpoint if pid == 0 else None
                schematic.create_location((bid, pid), coords, radius, [*labels], endpoint)
            endpoints.append((bid, pid))
    if definitions is not None:
        schematic.definition = definitions
    return schematic
