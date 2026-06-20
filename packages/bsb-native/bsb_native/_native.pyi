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

def connect_segments(
    lib_p: NDArray[np.float64],
    lib_q: NDArray[np.float64],
    lib_radius: NDArray[np.float64],
    lib_branch: NDArray[np.int64],
    lib_point: NDArray[np.int64],
    lib_offsets: NDArray[np.int64],
    pre_morpho: NDArray[np.int64],
    pre_rot: NDArray[np.float64],
    pre_pos: NDArray[np.float64],
    post_morpho: NDArray[np.int64],
    post_rot: NDArray[np.float64],
    post_pos: NDArray[np.float64],
    contact: float,
    favor: str = ...,
) -> tuple[NDArray[np.int64], NDArray[np.int64]]:
    """Connect two cell populations by morphology-segment (capsule) proximity.

    The morphology library is passed as flat per-segment arrays (``lib_*``) plus
    ``lib_offsets`` (length ``M+1``) delimiting each morphology's segment range.
    Each population is given as instances: a per-cell ``morpho`` index into the
    library, a per-cell ``(N, 3, 3)`` rotation matrix, and a per-cell ``(N, 3)``
    position. ``favor`` (``"pre"`` or ``"post"``) selects which side builds the
    trees. Returns ``(pre_locs, post_locs)``, each an ``(K, 3)`` int64 array of
    ``[cell, branch, point]`` triples aligned row-by-row, one per contact."""
