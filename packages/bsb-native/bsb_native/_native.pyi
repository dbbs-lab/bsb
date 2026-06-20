from numpy.typing import NDArray
import numpy as np

def poisson_disk(
    lo: tuple[float, float, float],
    hi: tuple[float, float, float],
    min_distance: float,
    k: int = ...,
    fixed: NDArray[np.float64] | None = ...,
    max_count: int | None = ...,
    seed: int = ...,
) -> NDArray[np.float64]:
    """Sample points in ``[lo, hi]`` no closer than ``min_distance`` to each
    other or to any ``fixed`` point. Returns an ``(N, 3)`` float64 array of the
    newly sampled points (``fixed`` points constrain but are not returned)."""

class SegmentTree:
    """Per-morphology segment BVH with an exact capsule query."""

    def __init__(
        self,
        seg_p: NDArray[np.float64],
        seg_q: NDArray[np.float64],
        seg_radius: NDArray[np.float64],
        seg_branch: NDArray[np.int64],
        seg_point: NDArray[np.int64],
    ) -> None: ...
    def __len__(self) -> int: ...
    def query_batch(
        self,
        q_p: NDArray[np.float64],
        q_q: NDArray[np.float64],
        q_radius: NDArray[np.float64],
        q_branch: NDArray[np.int64],
        q_point: NDArray[np.int64],
        q_cell: NDArray[np.int64],
        target_cell: int,
        contact: float,
    ) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
        """Match a batch of query segments (already in the tree's local frame)
        against the tree. Returns ``(target_locs, query_locs)``, each an
        ``(K, 3)`` int64 array of ``[cell, branch, point]`` triples, one row per
        contact within ``contact``."""
