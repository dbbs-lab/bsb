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

    A per-morphology segment bounding-volume hierarchy is built once per target
    morphology in its local frame; each candidate cell's segments are
    transformed into that frame and queried against the tree. The exact
    segment-to-segment (capsule) distance test is applied to every survivor, so
    reported contacts are exact. The cell-level box-tree prefilter of
    :class:`~bsb.connectivity.detailed.shared.Intersectional` bounds which cell
    pairs are considered.

    This is a faster, alternative path to :class:`VoxelIntersection`: it emits
    the same ``[cell, branch, point]`` location triples, so the two are
    interchangeable.

    :param contact_distance: distance, on top of the two segment radii, within
        which two segments form a contact.
    :param cache: cache target trees and reuse transformed morphologies.
    :param favor_cache: build the segment trees on the ``pre`` or ``post`` side;
        favor the side with fewer unique morphologies.
    """

    contact_distance = config.attr(type=float, default=0.0)
    cache = config.attr(type=bool, default=True)
    favor_cache = config.attr(type=types.in_(["pre", "post"]), default="pre")

    def connect(self, pre, post):
        if self.favor_cache == "pre":
            targets, candidates = pre, post
            target_morpho = self.presynaptic.morpho_loader
            cand_morpho = self.postsynaptic.morpho_loader
        else:
            targets, candidates = post, pre
            target_morpho = self.postsynaptic.morpho_loader
            cand_morpho = self.presynaptic.morpho_loader
        for target_set, cand_set, match_itr in self.candidate_intersection(
            targets, candidates
        ):
            tmset = target_morpho(target_set)
            cmset = cand_morpho(cand_set)
            self._match_segments(match_itr, target_set, cand_set, tmset, cmset)

    def _match_segments(self, matches, tset, cset, tmset, cmset):
        # Lazily import the compiled kernel: bsb-core stays importable without
        # the bsb-native wheel; only running this strategy requires it.
        from bsb_native import SegmentTree

        positions = tset.load_positions()
        rotations = tset.load_rotations()
        # Per-cell morphology-loader index: equal values share a morphology (and
        # therefore the same local-frame segments), so it is a stable cache key.
        morpho_index = tmset.get_indices(copy=False)
        crotations = cset.load_rotations()
        cpositions = cset.load_positions()

        # Group target cells by morphology so each segment tree is built once,
        # used for every cell that shares it, then dropped before the next
        # morphology. Peak memory is thus one tree (plus the current bucket's
        # transient candidate segments), independent of how many unique
        # morphologies the population has. The buckets themselves hold only
        # candidate index arrays, not geometry.
        buckets: dict = {}
        for target_id, candidates in enumerate(matches):
            if not len(candidates):
                continue
            buckets.setdefault(int(morpho_index[target_id]), []).append(
                (target_id, candidates)
            )

        src_acc = []
        dest_acc = []
        for members in buckets.values():
            # Build the tree from a representative cell's local-frame morphology;
            # every cell in the bucket shares those local segments.
            rep_id = members[0][0]
            tmor = tmset.get(rep_id, cache=self.cache, hard_cache=self.cache)
            tp, tq, tr, tb, tpt = _morpho_segments(tmor)
            if len(tp) == 0:
                continue
            tree = SegmentTree(tp, tq, tr, tb, tpt)
            if len(tree) == 0:
                continue
            for target_id, candidates in members:
                tpos = positions[target_id]
                trot = rotations[target_id]
                # Transform each candidate's segments into the target's local
                # frame: rotate by the candidate's own rotation, translate by the
                # relative offset, then anti-rotate by the target's rotation.
                qp, qq, qr, qb, qpt, qcell = [], [], [], [], [], []
                for cand in candidates:
                    morpho = cmset.get(cand, cache=self.cache, hard_cache=False)
                    morpho.rotate(crotations[cand])
                    morpho.translate(cpositions[cand] - tpos)
                    morpho.rotate(trot.inv())
                    sp, sq, sr, sb, spt = _morpho_segments(morpho)
                    if len(sp) == 0:
                        continue
                    qp.append(sp)
                    qq.append(sq)
                    qr.append(sr)
                    qb.append(sb)
                    qpt.append(spt)
                    qcell.append(np.full(len(sp), cand, dtype=np.int64))
                if not qp:
                    continue
                target_locs, cand_locs = tree.query_batch(
                    np.concatenate(qp),
                    np.concatenate(qq),
                    np.concatenate(qr),
                    np.concatenate(qb),
                    np.concatenate(qpt),
                    np.concatenate(qcell),
                    target_id,
                    self.contact_distance,
                )
                if len(target_locs):
                    src_acc.append(target_locs)
                    dest_acc.append(cand_locs)
            # `tree` is rebound (and the old one freed) on the next bucket.

        if not src_acc:
            return
        target_locs = np.concatenate(src_acc)
        cand_locs = np.concatenate(dest_acc)
        # Map target/candidate back to pre/post per `favor_cache`.
        if self.favor_cache == "pre":
            self.connect_cells(tset, cset, target_locs, cand_locs)
        else:
            self.connect_cells(cset, tset, cand_locs, target_locs)


def _morpho_segments(morpho):
    """Flatten a morphology into per-segment arrays in its current frame.

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
        np.ascontiguousarray(np.concatenate(starts)),
        np.ascontiguousarray(np.concatenate(ends)),
        np.concatenate(radii),
        np.concatenate(branch),
        np.concatenate(point),
    )


__all__ = ["SegmentIntersection"]
