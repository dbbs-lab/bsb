//! Bridson Poisson-disk sampling in a 3D box, with optional fixed points.
//!
//! `fixed` points are treated as already-placed neighbours (e.g. somas from
//! adjacent chunks read in as a halo): new samples respect `min_distance` to
//! them, but they are not themselves emitted. This is what lets per-chunk
//! sampling stay seamless across chunk borders when chunks are scheduled so
//! that touching chunks never run concurrently.
//!
//! Determinism: the sampler is driven entirely by `seed`, so the same inputs
//! reproduce the same output regardless of thread or platform.

use crate::geom::{dist2, Vec3};
use crate::rng::Rng;

/// A uniform background grid with at most one point per cell (guaranteed by the
/// cell size `min_distance / sqrt(3)`), for O(1) neighbour lookups.
struct Grid {
    origin: Vec3,
    cell: f64,
    dims: [usize; 3],
    /// -1 = empty, otherwise index into `points`.
    cells: Vec<i32>,
}

impl Grid {
    fn new(lo: Vec3, hi: Vec3, min_distance: f64) -> Self {
        let cell = min_distance / (3.0_f64).sqrt();
        let mut dims = [1usize; 3];
        for k in 0..3 {
            let span = (hi[k] - lo[k]).max(0.0);
            dims[k] = ((span / cell).ceil() as usize).max(1);
        }
        Grid {
            origin: lo,
            cell,
            dims,
            cells: vec![-1; dims[0] * dims[1] * dims[2]],
        }
    }

    #[inline]
    fn coord(&self, p: Vec3) -> [usize; 3] {
        let mut c = [0usize; 3];
        for k in 0..3 {
            let i = ((p[k] - self.origin[k]) / self.cell).floor() as isize;
            c[k] = i.clamp(0, self.dims[k] as isize - 1) as usize;
        }
        c
    }

    #[inline]
    fn idx(&self, c: [usize; 3]) -> usize {
        (c[2] * self.dims[1] + c[1]) * self.dims[0] + c[0]
    }

    fn insert(&mut self, p: Vec3, point_index: usize) {
        let c = self.coord(p);
        let i = self.idx(c);
        self.cells[i] = point_index as i32;
    }

    /// True if any stored point lies within `min_distance` of `p`.
    fn has_neighbor(&self, p: Vec3, points: &[Vec3], min_distance: f64) -> bool {
        let c = self.coord(p);
        let r2 = min_distance * min_distance;
        // r/sqrt(3) cells -> a violating point can be up to 2 cells away.
        for dz in -2isize..=2 {
            for dy in -2isize..=2 {
                for dx in -2isize..=2 {
                    let nx = c[0] as isize + dx;
                    let ny = c[1] as isize + dy;
                    let nz = c[2] as isize + dz;
                    if nx < 0
                        || ny < 0
                        || nz < 0
                        || nx >= self.dims[0] as isize
                        || ny >= self.dims[1] as isize
                        || nz >= self.dims[2] as isize
                    {
                        continue;
                    }
                    let stored =
                        self.cells[self.idx([nx as usize, ny as usize, nz as usize])];
                    if stored >= 0 && dist2(p, points[stored as usize]) < r2 {
                        return true;
                    }
                }
            }
        }
        false
    }
}

/// Sample points in `[lo, hi]` no closer than `min_distance` to each other or to
/// any `fixed` point. `k` is Bridson's attempts-per-active-sample (30 is typical).
/// If `max_count` is `Some(n)`, sampling stops once `n` points are emitted;
/// otherwise it fills to saturation. Only the newly sampled points are returned.
pub fn poisson_disk(
    lo: Vec3,
    hi: Vec3,
    min_distance: f64,
    k: usize,
    fixed: &[Vec3],
    max_count: Option<usize>,
    seed: u64,
) -> Vec<Vec3> {
    if min_distance <= 0.0 || hi[0] <= lo[0] || hi[1] <= lo[1] || hi[2] <= lo[2] {
        return Vec::new();
    }
    let mut rng = Rng::seeded(seed);
    let mut grid = Grid::new(lo, hi, min_distance);

    // All points (fixed first), so the grid can index them uniformly; outputs
    // are the points after `n_fixed`.
    let mut points: Vec<Vec3> = Vec::with_capacity(fixed.len() + 64);
    for &fp in fixed {
        let i = points.len();
        points.push(fp);
        grid.insert(fp, i);
    }
    let n_fixed = points.len();

    let span = [hi[0] - lo[0], hi[1] - lo[1], hi[2] - lo[2]];
    let sample_in_box = |rng: &mut Rng| -> Vec3 {
        [
            lo[0] + rng.unit() * span[0],
            lo[1] + rng.unit() * span[1],
            lo[2] + rng.unit() * span[2],
        ]
    };

    // Seed the active list with a valid initial point.
    let mut active: Vec<usize> = Vec::new();
    let reached =
        |points_len: usize| max_count.is_some_and(|m| points_len - n_fixed >= m);
    for _ in 0..64 {
        let p = sample_in_box(&mut rng);
        if !grid.has_neighbor(p, &points, min_distance) {
            let i = points.len();
            points.push(p);
            grid.insert(p, i);
            active.push(i);
            break;
        }
    }

    while !active.is_empty() && !reached(points.len()) {
        let ai = rng.range(active.len());
        let center = points[active[ai]];
        let mut found = false;
        for _ in 0..k {
            // Random point in the spherical annulus [min_distance, 2*min_distance].
            let radius = min_distance * (1.0 + rng.unit());
            // Uniform direction on the sphere.
            let u = 2.0 * rng.unit() - 1.0; // cos(theta) in [-1, 1]
            let phi = 2.0 * std::f64::consts::PI * rng.unit();
            let s = (1.0 - u * u).max(0.0).sqrt();
            let dir = [s * phi.cos(), s * phi.sin(), u];
            let cand = [
                center[0] + dir[0] * radius,
                center[1] + dir[1] * radius,
                center[2] + dir[2] * radius,
            ];
            if cand[0] < lo[0]
                || cand[0] >= hi[0]
                || cand[1] < lo[1]
                || cand[1] >= hi[1]
                || cand[2] < lo[2]
                || cand[2] >= hi[2]
            {
                continue;
            }
            if grid.has_neighbor(cand, &points, min_distance) {
                continue;
            }
            let i = points.len();
            points.push(cand);
            grid.insert(cand, i);
            active.push(i);
            found = true;
            if reached(points.len()) {
                break;
            }
            break;
        }
        if !found {
            active.swap_remove(ai);
        }
    }

    points.split_off(n_fixed)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn min_pairwise(points: &[Vec3]) -> f64 {
        let mut m = f64::INFINITY;
        for i in 0..points.len() {
            for j in (i + 1)..points.len() {
                m = m.min(dist2(points[i], points[j]).sqrt());
            }
        }
        m
    }

    #[test]
    fn respects_min_distance() {
        let pts = poisson_disk(
            [0., 0., 0.],
            [10., 10., 10.],
            1.0,
            30,
            &[],
            None,
            42,
        );
        assert!(pts.len() > 50, "expected a reasonable fill, got {}", pts.len());
        assert!(min_pairwise(&pts) >= 1.0 - 1e-9);
        for p in &pts {
            for k in 0..3 {
                assert!(p[k] >= 0.0 && p[k] < 10.0);
            }
        }
    }

    #[test]
    fn deterministic_with_seed() {
        let a = poisson_disk([0., 0., 0.], [8., 8., 8.], 1.0, 30, &[], None, 7);
        let b = poisson_disk([0., 0., 0.], [8., 8., 8.], 1.0, 30, &[], None, 7);
        assert_eq!(a.len(), b.len());
        for (x, y) in a.iter().zip(b.iter()) {
            assert_eq!(x, y);
        }
    }

    #[test]
    fn respects_fixed_points() {
        // Fixed points on a plane; new samples must keep min_distance to them.
        let fixed: Vec<Vec3> = (0..10)
            .flat_map(|i| (0..10).map(move |j| [i as f64, j as f64, 0.5]))
            .collect();
        let pts = poisson_disk(
            [0., 0., 0.],
            [10., 10., 10.],
            1.0,
            30,
            &fixed,
            None,
            123,
        );
        for p in &pts {
            for f in &fixed {
                assert!(dist2(*p, *f).sqrt() >= 1.0 - 1e-9);
            }
        }
    }

    #[test]
    fn honors_max_count() {
        let pts = poisson_disk(
            [0., 0., 0.],
            [50., 50., 50.],
            1.0,
            30,
            &[],
            Some(25),
            9,
        );
        assert_eq!(pts.len(), 25);
    }
}
