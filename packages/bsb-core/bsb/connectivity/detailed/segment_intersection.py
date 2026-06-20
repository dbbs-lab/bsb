import numpy as np

from ... import config
from ...config import types
from ..strategy import ConnectionStrategy
from .shared import Intersectional


@config.node
class SegmentIntersection(Intersectional, ConnectionStrategy):
    """
    Connect cells whose morphology branches, treated as 3D capsules (line
    segments with a radius), come within ``contact_distance`` of each other.

    The whole geometric search runs in the ``bsb-native`` Rust kernel: a
    cell-level BVH (TLAS) over instances does the broad phase, a per-morphology
    segment BVH (BLAS) is built once per unique morphology, and the exact
    segment-to-segment (capsule) distance test is applied to every survivor.
    Python only loads the populations from storage and passes flat arrays; no
    per-pair work happens in Python. The chunk-level region of interest of
    :class:`~bsb.connectivity.detailed.shared.Intersectional` still bounds which
    chunks a job loads.

    Emits the same ``[cell, branch, point]`` location triples as
    :class:`VoxelIntersection`, so the two are interchangeable.

    :param contact_distance: distance, on top of the two segment radii, within
        which two segments form a contact.
    :param favor_cache: build the segment trees on the ``pre`` or ``post`` side;
        favor the side with fewer unique morphologies.
    """

    contact_distance = config.attr(type=float, default=0.0)
    favor_cache = config.attr(type=types.in_(["pre", "post"]), default="pre")

    def connect(self, pre, post):
        for pre_set in pre.placement:
            for post_set in post.placement:
                self._connect_sets(pre_set, post_set)

    def _connect_sets(self, pre_set, post_set):
        # Lazily import the compiled kernel: bsb-core stays importable without
        # the bsb-native wheel; only running this strategy requires it.
        from bsb_native import connect_segments

        pre_ms = self.presynaptic.morpho_loader(pre_set)
        post_ms = self.postsynaptic.morpho_loader(post_set)
        library, pre_idx, post_idx = _build_library(pre_ms, post_ms)
        flat = _flatten_library(library)
        if flat is None:
            return  # no morphology has any segments
        lib_p, lib_q, lib_r, lib_b, lib_pt, lib_off = flat

        pre_pos = np.ascontiguousarray(pre_set.load_positions(), dtype=float)
        post_pos = np.ascontiguousarray(post_set.load_positions(), dtype=float)
        if len(pre_pos) == 0 or len(post_pos) == 0:
            return

        pre_locs, post_locs = connect_segments(
            lib_p,
            lib_q,
            lib_r,
            lib_b,
            lib_pt,
            lib_off,
            pre_idx,
            _rotation_matrices(pre_set),
            pre_pos,
            post_idx,
            _rotation_matrices(post_set),
            post_pos,
            self.contact_distance,
            self.favor_cache,
            self.affinity,
            0,
        )
        if len(pre_locs):
            self.connect_cells(pre_set, post_set, pre_locs, post_locs)


def _build_library(pre_ms, post_ms):
    """Build one shared morphology library across both populations.

    Returns ``(library, pre_idx, post_idx)``: ``library`` is a list of
    per-morphology segment tuples (deduplicated by morphology name), and the two
    index arrays map each cell to its library entry. Equal names are the same
    stored morphology, so they share one library entry and one tree.
    """
    library = []
    name_to_idx: dict = {}

    def index_set(ms):
        remap = []
        for name, morpho in zip(ms.names, ms.iter_morphologies(unique=True)):
            idx = name_to_idx.get(name)
            if idx is None:
                idx = len(library)
                name_to_idx[name] = idx
                library.append(_morpho_segments(morpho))
            remap.append(idx)
        per_cell = ms.get_indices()
        if len(per_cell) == 0:
            return np.empty(0, dtype=np.int64)
        return np.asarray(remap, dtype=np.int64)[per_cell]

    return library, index_set(pre_ms), index_set(post_ms)


def _flatten_library(library):
    """Concatenate the library into flat per-segment arrays + offsets, or return
    ``None`` if no morphology has any segments."""
    ps, qs, rs, bs, pts, off = [], [], [], [], [], [0]
    for starts, ends, radii, branch, point in library:
        ps.append(starts)
        qs.append(ends)
        rs.append(radii)
        bs.append(branch)
        pts.append(point)
        off.append(off[-1] + len(starts))
    if off[-1] == 0:
        return None
    return (
        np.ascontiguousarray(np.concatenate(ps)),
        np.ascontiguousarray(np.concatenate(qs)),
        np.concatenate(rs),
        np.concatenate(bs),
        np.concatenate(pts),
        np.asarray(off, dtype=np.int64),
    )


def _rotation_matrices(pset):
    """Per-cell ``(N, 3, 3)`` rotation matrices for a placement set."""
    mats = np.array(
        [r.as_matrix() for r in pset.load_rotations().iter()], dtype=float
    )
    if mats.ndim != 3:
        mats = mats.reshape(-1, 3, 3)
    return np.ascontiguousarray(mats)


def _morpho_segments(morpho):
    """Flatten a morphology into per-segment arrays in its local frame.

    Returns ``(starts, ends, radii, branch, point)``: the ``(M, 3)`` segment
    endpoints, the ``(M,)`` mean segment radius, and the ``(M,)`` branch id and
    in-branch start-point id reported on a contact.
    """
    starts, ends, radii, branch, point = [], [], [], [], []
    for bid, b in enumerate(morpho.branches):
        pts = np.asarray(b.points, dtype=float)
        n = len(pts)
        if n < 2:
            continue
        r = np.asarray(b.radii, dtype=float)
        starts.append(pts[:-1])
        ends.append(pts[1:])
        radii.append((r[:-1] + r[1:]) * 0.5)
        branch.append(np.full(n - 1, bid, dtype=np.int64))
        point.append(np.arange(n - 1, dtype=np.int64))
    if not starts:
        empty3 = np.empty((0, 3), dtype=float)
        empty_i = np.empty(0, dtype=np.int64)
        return empty3, empty3, np.empty(0, dtype=float), empty_i, empty_i
    return (
        np.concatenate(starts),
        np.concatenate(ends),
        np.concatenate(radii),
        np.concatenate(branch),
        np.concatenate(point),
    )


__all__ = ["SegmentIntersection"]
