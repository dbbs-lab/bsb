import zlib

import numpy as np

from .. import config
from ..voxels import VoxelSet
from .strategy import PlacementStrategy


@config.node
class PoissonDiskPlacement(PlacementStrategy):
    """
    Place cells by Poisson-disk sampling, so no two somas are closer than
    ``min_distance``. Backed by the ``bsb-native`` Bridson kernel.

    ``min_distance`` is the hard constraint; the indicated count/density is
    treated as an upper bound on how many cells are placed. If you need an exact
    count rather than a spacing guarantee, use :class:`RandomPlacement`.

    Chunks are sampled independently with a deterministic per-chunk seed, so the
    minimum-distance guarantee holds within a chunk; it can be violated right at
    chunk borders. A seamless cross-chunk mode (a neighbour halo with colored
    wavefront scheduling) is planned.

    :param min_distance: minimum distance between somas. If omitted, it is
        derived from the indicated count and the region volume, and never goes
        below twice the soma radius.
    :param tries: Bridson attempts per active sample.
    :param seed: base seed, combined with the chunk coordinates and cell-type
        name for reproducibility.
    """

    min_distance = config.attr(type=float, required=False)
    tries = config.attr(type=int, default=30)
    seed = config.attr(type=int, required=False)

    def place(self, chunk, indicators):
        # Lazily import the compiled kernel: bsb-core stays importable without
        # the bsb-native wheel; only running this strategy requires it.
        from bsb_native import poisson_disk

        voxels = VoxelSet.concatenate(
            *(p.chunk_to_voxels(chunk) for p in self.partitions)
        )
        if voxels.is_empty:
            return
        lo, hi = voxels.bounds
        boxes = voxels.as_boxes()
        single_voxel = len(boxes) == 1
        for name, indicator in indicators.items():
            count = int(np.sum(indicator.guess(chunk, voxels)))
            if count <= 0:
                continue
            min_distance = self._derive_min_distance(
                lo, hi, count, indicator.get_radius()
            )
            positions = poisson_disk(
                tuple(float(x) for x in lo),
                tuple(float(x) for x in hi),
                min_distance,
                self.tries,
                None,
                count,
                self._chunk_seed(chunk, name),
            )
            if len(positions) == 0:
                continue
            # Reject samples that fall in a gap between voxels of a sparse region.
            if not single_voxel:
                positions = positions[_inside_any(positions, boxes)]
                if len(positions) == 0:
                    continue
            self.place_cells(indicator, positions, chunk)

    def _derive_min_distance(self, lo, hi, count, radius):
        if self.min_distance is not None:
            return float(self.min_distance)
        volume = float(np.prod(np.asarray(hi, dtype=float) - np.asarray(lo, dtype=float)))
        # Spacing of a regular lattice of `count` points in the region, floored at
        # two soma radii so somas cannot overlap.
        spacing = (volume / count) ** (1 / 3) if volume > 0 else 0.0
        return max(spacing, 2 * radius)

    def _chunk_seed(self, chunk, name):
        base = 0 if self.seed is None else int(self.seed)
        cx, cy, cz = (int(c) for c in chunk)
        # Mix the base seed, chunk coordinates and (stable) cell-type name so each
        # chunk samples reproducibly and differently.
        h = (
            (base * 0x9E3779B1)
            ^ (cx * 73856093)
            ^ (cy * 19349663)
            ^ (cz * 83492791)
            ^ zlib.crc32(name.encode())
        )
        return h & 0xFFFFFFFFFFFFFFFF


def _inside_any(positions, boxes):
    """Mask of positions falling inside any of the ``(M, 6)`` voxel boxes."""
    lo = boxes[:, :3]
    hi = boxes[:, 3:]
    inside = np.all(
        (positions[:, None, :] >= lo[None, :, :])
        & (positions[:, None, :] < hi[None, :, :]),
        axis=2,
    )
    return inside.any(axis=1)


__all__ = ["PoissonDiskPlacement"]
