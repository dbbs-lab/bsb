import itertools
import zlib

import numpy as np

from .. import config
from ..storage._chunks import Chunk
from ..voxels import VoxelSet
from .strategy import PlacementStrategy

_NEIGHBORS = [d for d in itertools.product((-1, 0, 1), repeat=3) if d != (0, 0, 0)]


def _color(chunk):
    # 8 parity classes; same-color chunks are never face/edge/corner adjacent.
    return (int(chunk[0]) % 2) * 4 + (int(chunk[1]) % 2) * 2 + (int(chunk[2]) % 2)


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
    seamless = config.attr(type=bool, default=True)

    def queue(self, pool, chunk_size):
        """Queue placement jobs.

        In seamless mode, color each chunk by the parity of its coordinates (8
        classes) and make every chunk depend on its lower-color neighbours. Since
        same-color chunks are never adjacent, this schedules placement in 8
        wavefronts where no two touching chunks ever run at once: when a chunk is
        placed, its already-placed neighbours can be read as a fixed halo, and
        every chunk border is reconciled exactly once. Falls back to the default
        per-chunk queueing when ``seamless`` is off.
        """
        if not self.seamless:
            return super().queue(pool, chunk_size)
        base_deps = set(
            itertools.chain(
                *(pool.get_submissions_of(strat) for strat in self.get_deps())
            )
        )
        chunks = np.unique(
            np.concatenate([p.to_chunks(chunk_size) for p in self.partitions]), axis=0
        )
        chunk_set = {tuple(int(c) for c in ch) for ch in chunks}
        jobs: dict = {}
        # Process in color order so a chunk's lower-color neighbour jobs already
        # exist when it is queued.
        for ch in sorted(chunk_set, key=lambda c: (_color(c), c)):
            col = _color(ch)
            deps = set(base_deps)
            for d in _NEIGHBORS:
                nb = (ch[0] + d[0], ch[1] + d[1], ch[2] + d[2])
                if nb in chunk_set and _color(nb) < col:
                    deps.add(jobs[nb])
            jobs[ch] = pool.queue_placement(
                self, Chunk(np.array(ch), chunk_size), deps=deps
            )

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
            # Already-placed neighbours within reach act as fixed constraints, so
            # samples near the border respect them (see `queue`).
            fixed = (
                self._halo(indicator.cell_type, chunk, lo, hi, min_distance)
                if self.seamless
                else None
            )
            positions = poisson_disk(
                tuple(float(x) for x in lo),
                tuple(float(x) for x in hi),
                min_distance,
                self.tries,
                fixed,
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

    def _halo(self, cell_type, chunk, lo, hi, min_distance):
        # Read this cell type's already-placed somas in the 26 neighbour chunks
        # and keep those within `min_distance` of the sampling box, to seed the
        # sampler as fixed constraints. Higher-color neighbours are not placed yet
        # (they depend on this chunk), so they simply contribute nothing.
        base = np.asarray(chunk, dtype=int)
        neighbors = [Chunk(base + d, chunk.dimensions) for d in _NEIGHBORS]
        positions = cell_type.get_placement_set(chunks=neighbors).load_positions()
        if len(positions) == 0:
            return None
        lo_h = np.asarray(lo, dtype=float) - min_distance
        hi_h = np.asarray(hi, dtype=float) + min_distance
        mask = np.all((positions >= lo_h) & (positions <= hi_h), axis=1)
        positions = np.ascontiguousarray(positions[mask], dtype=float)
        return positions if len(positions) else None

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
