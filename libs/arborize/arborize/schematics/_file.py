import itertools
import os
import re
import tempfile
import typing
from typing import Optional, TextIO, Union

from morphio import Morphology, SomaType

from ..schematic import Schematic

if typing.TYPE_CHECKING:
    from ..definitions import Definition


def file_schematic(
    file_like: Union["str", "os.PathLike", TextIO],
    definitions: Optional["Definition"] = None,
    fname: str = None,
    *,
    name=None,
) -> Schematic:
    if hasattr(file_like, "read"):
        if not file_like.name and not fname:
            raise OSError(
                "The file-driver MorphIO requires a file name to parse files. "
                "Use a file-like object that provides a `name` attribute, "
                "or pass the `fname` keyword argument, "
                "with a suffix matching the file format."
            )
        base = os.path.basename(file_like.name or fname)
        handle, abspath = tempfile.mkstemp(suffix=base)
        os.close(handle)
        try:
            with open(abspath, "w") as f:
                if file_like.seekable():
                    file_like.seek(0)
                f.write(file_like.read())
            return file_schematic(abspath, definitions)
        finally:
            os.unlink(abspath)

    morpho = Morphology(os.fspath(file_like))
    schematic = Schematic(name=name)
    branches = [
        morpho.soma,
        *itertools.chain.from_iterable(s.iter() for s in morpho.root_sections),
    ]
    endpoints = []
    for bid, branch in enumerate(branches):
        mid = getattr(branch, "id", -1) + 1
        if bid != mid:
            raise AssertionError("MorphIO deviated from depth-first order.")
        parent = _get_parent(morpho, branch)
        if not len(branch.points):
            true_parent = None
            while True:
                if parent is None:
                    break
                elif len(parent.points):
                    true_parent = endpoints[getattr(parent, "id", -1) + 1]
                    break
                parent = None if branch.is_root else branch.parent
            schematic.create_empty()
            endpoints.append(true_parent)
        else:
            if parent is not None:
                endpoint = endpoints[getattr(parent, "id", -1) + 1]
            else:
                endpoint = None
            if isinstance(branch.type, SomaType):
                branch_type = "soma"
            elif "custom" in str(branch.type):
                num = re.search(r"\d+$", str(branch.type)).group()
                branch_type = f"tag_{num}"
            else:
                branch_type = str(branch.type).split(".")[-1]
            for pid, coords, diam in zip(
                itertools.count(), branch.points, branch.diameters
            ):
                endpoint = endpoint if pid == 0 else None
                schematic.create_location(
                    (bid, pid), coords, diam / 2, [branch_type], endpoint
                )
            endpoints.append((bid, pid))
    if definitions is not None:
        schematic.definition = definitions
    return schematic


def _get_parent(morpho: Morphology, branch):
    # Does the morphology have a soma? If so, the roots are connected to it.
    root_parent = morpho.soma if morpho.soma else None
    if hasattr(branch, "is_root"):
        return root_parent if branch.is_root else branch.parent
    else:
        # The soma never has a parent
        return None
