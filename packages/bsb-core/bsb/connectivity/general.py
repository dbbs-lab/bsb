import numpy as np

from .. import config
from ..config import types
from ..exceptions import ConnectivityError
from ..mixins import InvertedRoI
from .strategy import ConnectionStrategy, roi_key


@config.node
class AllToAll(ConnectionStrategy):
    """
    All to all connectivity between two neural populations.
    """

    affinity: float = config.attr(type=types.float(0.0, 1.0), required=False, default=1.0)
    """
    Probability for each individual connection to be, default is 1, i.e. all connected.
    """

    def connect(self, pre, post):
        for from_ps in pre.placement:
            fl = len(from_ps)
            for to_ps in post.placement:
                len_ = len(to_ps)
                ml = fl * len_
                # Keyed on the strategy, the cell type pair and the chunks involved, so
                # every rank draws the same connections for the same chunk pair.
                rng = self.get_rng(
                    key=(
                        "connectivity",
                        self.name,
                        from_ps.cell_type.name,
                        to_ps.cell_type.name,
                        roi_key(pre),
                        roi_key(post),
                    ),
                )
                filtered_ = rng.binomial(1, p=self.affinity, size=ml) > 0
                ml = np.count_nonzero(filtered_)
                src_locs = np.full((ml, 3), -1)
                dest_locs = np.full((ml, 3), -1)
                src_locs[:, 0] = np.repeat(np.arange(fl), len_)[filtered_]
                dest_locs[:, 0] = np.tile(np.arange(len_), fl)[filtered_]
                self.connect_cells(from_ps, to_ps, src_locs, dest_locs)


def _connect_fixed_degree(self, pre, post, degree, is_in):
    # Generalized connect function for Fixed in- and out-degree
    # Keyed on the strategy and the chunks involved, so every rank draws the same
    # targets for the same chunk pair.
    rng = self.get_rng(
        key=(
            "connectivity",
            self.name,
            "fixed_degree",
            roi_key(pre),
            roi_key(post),
        ),
    )
    ps_counted = pre.placement if is_in else post.placement
    ps_fixed = post.placement if is_in else pre.placement
    high = sum(len(ps) for ps in ps_counted)
    if high < degree:
        raise ConnectivityError(
            f"Number of cells for dependant population ({high}) is too small to match "
            f"required degree value {degree} for connection strategy {self.name}"
        )
    for ps in ps_fixed:
        l_ = len(ps)
        self_idx = _self_indices(self, ps, ps_counted)
        if np.any(self_idx >= 0) and high - 1 < degree:
            raise ConnectivityError(
                f"Number of cells for dependant population other than the cell itself "
                f"({high - 1}) is too small to match required degree value {degree} for "
                f"connection strategy {self.name}. Set `allow_autapses` to allow cells "
                "to connect to themselves."
            )
        counted_targets = np.full((l_ * degree, 3), -1)
        fixed_targets = np.full((l_ * degree, 3), -1)
        ptr = 0
        for i in range(l_):
            fixed_targets[ptr : ptr + degree, 0] = i
            if self_idx[i] < 0:
                drawn = rng.choice(high, degree, replace=False)
            else:
                # Draw among the other cells only, so the degree stays exact.
                drawn = rng.choice(high - 1, degree, replace=False)
                drawn[drawn >= self_idx[i]] += 1
            counted_targets[ptr : ptr + degree, 0] = drawn
            ptr += degree
        lowmux = 0
        for ps_o in ps_counted:
            highmux = lowmux + len(ps_o)
            demux_idx = (counted_targets[:, 0] >= lowmux) & (
                counted_targets[:, 0] < highmux
            )
            demuxed = counted_targets[demux_idx]
            demuxed[:, 0] -= lowmux
            if is_in:
                self.connect_cells(ps_o, ps, demuxed, fixed_targets[demux_idx])
            else:
                self.connect_cells(ps, ps_o, fixed_targets[demux_idx], demuxed)
            lowmux = highmux


def _self_indices(self, ps, ps_counted):
    # Index of each cell of `ps` among the concatenated counted populations, or -1 if
    # it is not part of them (or if autapses are allowed).
    self_idx = np.full(len(ps), -1)
    if self.allow_autapses:
        return self_idx
    lowmux = 0
    for ps_o in ps_counted:
        if ps_o.cell_type is ps.cell_type and len(ps_o):
            counted_ids = ps_o.load_ids()
            fixed_ids = ps.load_ids()
            order = np.argsort(counted_ids)
            found = np.searchsorted(counted_ids, fixed_ids, sorter=order)
            found = np.minimum(found, len(counted_ids) - 1)
            match = counted_ids[order[found]] == fixed_ids
            self_idx[match] = lowmux + order[found[match]]
        lowmux += len(ps_o)
    return self_idx


@config.node
class FixedIndegree(InvertedRoI, ConnectionStrategy):
    """
    Connect a group of postsynaptic cell types to ``indegree`` uniformly random
    presynaptic cells from all the presynaptic cell types.
    """

    indegree: int = config.attr(type=int, required=True)
    """
    Number of postsynaptic cell to connect to each presynaptic cell.
    """

    def connect(self, pre, post):
        _connect_fixed_degree(self, pre, post, self.indegree, True)


@config.node
class FixedOutdegree(ConnectionStrategy):
    """
    Connect a group of presynaptic cell types to ``outdegree`` uniformly random
    postsynaptic cells from all the postsynaptic cell types.
    """

    outdegree: int = config.attr(type=int, required=True)
    """
    Number of presynaptic cell to connect to each postsynaptic cell.
    """

    def connect(self, pre, post):
        _connect_fixed_degree(self, pre, post, self.outdegree, False)


__all__ = ["AllToAll", "FixedIndegree", "FixedOutdegree"]
