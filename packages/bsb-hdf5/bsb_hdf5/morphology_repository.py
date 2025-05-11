import itertools
import json

import numpy as np
from bsb import (
    Branch,
    MissingMorphologyError,
    Morphology,
    MorphologyRepositoryError,
    StoredMorphology,
)
from bsb import MorphologyRepository as IMorphologyRepository
from bsb._encoding import EncodedLabels

from .resource import HANDLED, Resource, handles_handles

_root = "/morphologies"


class MetaEncoder(json.JSONEncoder):
    """
    Encodes morphology metadata to JSON.
    """

    def default(self, o):
        if isinstance(o, np.ndarray):
            arr = o.tolist()
            arr.append("__ndarray__")
            return arr
        else:
            super().default(o)


def meta_object_hook(obj):
    for k, v in obj.items():
        if isinstance(v, list) and v[-1] == "__ndarray__":
            v.pop()
            obj[k] = np.array(v)
    return obj


class MorphologyRepository(Resource, IMorphologyRepository):
    def __init__(self, engine):
        super().__init__(engine, _root)

    def select(self, *selectors):
        if not selectors:
            return []
        all_loaders = self.all()
        selected = []
        for selector in selectors:
            selector.validate(all_loaders)
            selected.extend(filter(selector.pick, all_loaders))
        return selected

    @handles_handles("r")
    def preload(self, name, meta=None, handle=HANDLED):
        return StoredMorphology(
            name,
            self._make_loader(name, meta),
            meta if meta is not None else self.get_meta(name, handle=handle),
        )

    def _make_loader(self, name, meta):
        def loader():
            return self.load(name, preloaded_meta=meta)

        return loader

    @handles_handles("r")
    def get_meta(self, name, handle=HANDLED):
        all_meta = self.get_all_meta(handle=handle)
        try:
            meta = all_meta[name]
        except KeyError:
            raise MissingMorphologyError(
                f"`{self._engine.root}` contains no morphology named `{name}`."
            ) from None
        return meta

    @handles_handles("r")
    def get_all_meta(self, handle=HANDLED):
        if "morphology_meta" not in handle:
            return {}
        return json.loads(handle["morphology_meta"][()], object_hook=meta_object_hook)

    @handles_handles("a")
    def update_all_meta(self, meta, handle=HANDLED):
        all_meta = self.get_all_meta(handle=handle)
        all_meta.update(meta)
        self.set_all_meta(all_meta, handle=handle)

    @handles_handles("a")
    def set_all_meta(self, all_meta, handle=HANDLED):
        if "morphology_meta" in handle:
            del handle["morphology_meta"]
        handle.create_dataset(
            "morphology_meta", data=json.dumps(all_meta, cls=MetaEncoder)
        )

    @handles_handles("r")
    def all(self, handle=HANDLED):
        all_meta = self.get_all_meta(handle=handle)
        return [
            self.preload(name, meta=meta, handle=handle)
            for name, meta in all_meta.items()
        ]

    @handles_handles("r")
    def has(self, name, handle=HANDLED):
        return f"{self._path}/{name}" in handle

    @handles_handles("r")
    def load(self, name, preloaded_meta=None, handle=HANDLED):
        try:
            root = handle[f"{self._path}/{name}/"]
        except Exception:
            raise MissingMorphologyError(
                f"`{self._engine.root}` contains no morphology named `{name}`."
            ) from None
        data = root["data"][()]
        points = data[:, :3].copy()
        radii = data[:, 3].copy()
        # Turns the forced JSON str keys back into ints
        labelsets = {
            int(k): v for k, v in json.loads(root["data"].attrs["labels"]).items()
        }
        labels = EncodedLabels(
            len(points), buffer=data[:, 4].astype(int), labels=labelsets
        )
        prop_names = root["data"].attrs["properties"]
        props = dict(zip(prop_names, np.rollaxis(data[:, 5:], 1), strict=False))
        parents = {-1: None}
        branch_id = itertools.count()
        roots = []
        ptr = 0
        for nptr, p in root["graph"][()]:
            radii[ptr:nptr]
            labels[ptr:nptr]
            {k: v[ptr:nptr] for k, v in props.items()}
            branch = Branch(
                points[ptr:nptr],
                radii[ptr:nptr],
                labels[ptr:nptr],
                {k: v[ptr:nptr] for k, v in props.items()},
            )
            parent = parents.get(p)
            parents[next(branch_id)] = branch
            if parent:
                parent.attach_child(branch)
            else:
                roots.append(branch)
            ptr = nptr
        if preloaded_meta is None:
            meta = self.get_meta(name, handle=handle)
        else:
            meta = preloaded_meta
        morpho = Morphology(roots, meta, shared_buffers=(points, radii, labels, props))
        assert morpho._check_shared(), "Morpho read with unshareable buffers"
        return morpho

    @handles_handles("a")
    def save(self, name, morphology, overwrite=False, update_meta=True, handle=HANDLED):
        me = handle[self._path]
        if self.has(name):
            if overwrite:
                self.remove(name)
            else:
                root = self._engine.root
                raise MorphologyRepositoryError(
                    f"A morphology called '{name}' already exists in `{root}`."
                )
        root = me.create_group(name)
        # Optimizing a morphology goes through the same steps as what is required
        # to save it to disk; plus, now the user's object is optimized :)
        morphology.optimize()
        branches = morphology.branches
        n_prop = len(morphology._shared._prop)
        data = np.empty((len(morphology), 5 + n_prop))
        data[:, :3] = morphology._shared._points
        data[:, 3] = morphology._shared._radii
        data[:, 4] = morphology._shared._labels
        for i, prop in enumerate(morphology._shared._prop.values()):
            data[:, 5 + i] = prop
        dds = root.create_dataset("data", data=data)
        dds.attrs["labels"] = json.dumps(
            {k: list(v) for k, v in morphology._shared._labels.labels.items()}
        )
        dds.attrs["properties"] = [*morphology._shared._prop.keys()]
        graph = np.empty((len(branches), 2))
        parents = {None: -1}
        ptr = 0
        for i, branch in enumerate(morphology.branches):
            ptr += len(branch)
            graph[i, 0] = ptr
            graph[i, 1] = parents[branch.parent]
            parents[branch] = i
        root.create_dataset("graph", data=graph, dtype=int)
        morphology.meta["name"] = name
        if len(morphology._shared._points):
            morphology.meta["ldc"] = np.min(morphology._shared._points, axis=0)
            morphology.meta["mdc"] = np.max(morphology._shared._points, axis=0)
        else:
            morphology.meta["ldc"] = morphology.meta["mdc"] = np.nan
        if update_meta:
            all_meta = self.get_all_meta(handle=handle)
            all_meta[name] = morphology.meta
            self.set_all_meta(all_meta)
        return StoredMorphology(name, lambda: morphology, morphology.meta)

    @handles_handles("a")
    def remove(self, name, handle=HANDLED):
        try:
            del handle[f"{self._path}/{name}"]
        except KeyError:
            raise MorphologyRepositoryError(f"'{name}' doesn't exist.") from None
