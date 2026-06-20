//! Whole-connection kernel: given a morphology library and the two cell
//! populations as instances (morphology index + rotation + position), find every
//! pair of cells whose morphology segments come within a contact distance, and
//! return the `[cell, branch, point]` location triples.
//!
//! This is the full two-level instanced traversal in Rust: a TLAS (BVH over cell
//! world-boxes) for the cell-level broad phase, a BLAS (per-morphology segment
//! BVH) built once per unique target morphology, and the per-cell transforms.
//! Python only loads the data from storage and passes flat arrays; no per-pair
//! work happens in Python.

use crate::bvh::{AabbBvh, Segment, SegmentTree};
use crate::geom::{matvec, matvec_t, Aabb, Mat3, Vec3};
use crate::rng::Rng;
use rayon::prelude::*;

/// One cell population as instances of morphologies in the shared library.
pub struct Instances<'a> {
    /// Per cell: index into the morphology library.
    pub morpho: &'a [u32],
    /// Per cell: rotation matrix.
    pub rot: &'a [Mat3],
    /// Per cell: position.
    pub pos: &'a [Vec3],
}

impl Instances<'_> {
    fn len(&self) -> usize {
        self.morpho.len()
    }
}

/// Which side builds the BLAS/TLAS (the "targets"); the other side is streamed
/// as queries. Favor the side with fewer unique morphologies.
#[derive(Clone, Copy)]
pub enum Favor {
    Pre,
    Post,
}

/// Keep a random fraction `affinity` of the candidate cells, in place. Matches
/// the per-target candidate subsampling of the legacy `Intersectional` strategy:
/// keep `floor(n*affinity)` plus one more with probability of the fractional part.
fn subsample(cands: &mut Vec<usize>, affinity: f64, rng: &mut Rng) {
    let n = cands.len();
    let exact = n as f64 * affinity;
    let floor = exact.floor();
    let keep = floor as usize + usize::from(rng.unit() < (exact - floor));
    if keep >= n {
        return;
    }
    // Partial Fisher-Yates: shuffle `keep` random elements to the front, truncate.
    for i in 0..keep {
        let j = i + rng.range(n - i);
        cands.swap(i, j);
    }
    cands.truncate(keep);
}

/// Returns `(pre_locs, post_locs)`: matched `[cell, branch, point]` triples, one
/// row per contact, aligned so row `i` of each is the two ends of one contact.
///
/// `affinity` in `[0, 1]` keeps that random fraction of each query cell's
/// candidate partners (1.0 = no subsampling); `seed` makes that reproducible.
pub fn connect_segments(
    library: &[Vec<Segment>],
    pre: &Instances,
    post: &Instances,
    contact: f64,
    favor: Favor,
    affinity: f64,
    seed: u64,
) -> (Vec<[i64; 3]>, Vec<[i64; 3]>) {
    let (targets, queries, target_is_pre) = match favor {
        Favor::Pre => (pre, post, true),
        Favor::Post => (post, pre, false),
    };
    let n_morpho = library.len();

    // Per-morphology local AABB (radius already folded into each segment box).
    let local_box: Vec<Aabb> = library
        .iter()
        .map(|segs| {
            let mut b = Aabb::empty();
            for s in segs {
                b.expand(&Aabb::from_segment(s.p, s.q, s.radius));
            }
            b
        })
        .collect();

    // Build a BLAS only for the morphologies the targets actually use.
    let mut used = vec![false; n_morpho];
    for &m in targets.morpho {
        used[m as usize] = true;
    }
    let blas: Vec<Option<SegmentTree>> = (0..n_morpho)
        .into_par_iter()
        .map(|m| {
            if used[m] && !library[m].is_empty() {
                Some(SegmentTree::build(library[m].clone()))
            } else {
                None
            }
        })
        .collect();

    // TLAS over target cells (world boxes already include radius).
    let t_boxes: Vec<Aabb> = (0..targets.len())
        .map(|i| local_box[targets.morpho[i] as usize].transformed(&targets.rot[i], targets.pos[i]))
        .collect();
    let tlas = AabbBvh::build(t_boxes);
    if tlas.is_empty() {
        return (Vec::new(), Vec::new());
    }

    // Each query cell, in parallel: broad-phase against the TLAS, then exact
    // capsule queries against each candidate target's BLAS.
    let per_query: Vec<(Vec<[i64; 3]>, Vec<[i64; 3]>)> = (0..queries.len())
        .into_par_iter()
        .map(|qi| {
            let qm = queries.morpho[qi] as usize;
            let qsegs = &library[qm];
            if qsegs.is_empty() {
                return (Vec::new(), Vec::new());
            }
            let r_q = &queries.rot[qi];
            let p_q = queries.pos[qi];
            let mut qbox = local_box[qm].transformed(r_q, p_q);
            qbox.pad(contact);

            let mut candidates = tlas.query_aabb(&qbox);
            if affinity < 1.0 && !candidates.is_empty() {
                // Per-query RNG keyed on (seed, qi) so subsampling is
                // reproducible and independent of thread scheduling.
                let mut rng =
                    Rng::seeded(seed ^ (qi as u64).wrapping_mul(0x9E3779B97F4A7C15));
                subsample(&mut candidates, affinity, &mut rng);
            }

            let mut a_locs: Vec<[i64; 3]> = Vec::new(); // target side
            let mut b_locs: Vec<[i64; 3]> = Vec::new(); // query side
            for ti in candidates {
                let tree = match &blas[targets.morpho[ti] as usize] {
                    Some(t) => t,
                    None => continue,
                };
                let r_t = &targets.rot[ti];
                let p_t = targets.pos[ti];
                // Bring each query segment into this target's local frame:
                // R_t^T (R_q x + p_q - p_t).
                for s in qsegs {
                    let lp = to_local(r_t, p_t, r_q, p_q, s.p);
                    let lq = to_local(r_t, p_t, r_q, p_q, s.q);
                    for tree_seg in tree.query(lp, lq, s.radius, contact) {
                        let (tb, tp) = tree.location(tree_seg);
                        a_locs.push([ti as i64, tb, tp]);
                        b_locs.push([qi as i64, s.branch, s.point]);
                    }
                }
            }
            (a_locs, b_locs)
        })
        .collect();

    let mut a_all: Vec<[i64; 3]> = Vec::new();
    let mut b_all: Vec<[i64; 3]> = Vec::new();
    for (a, b) in per_query {
        a_all.extend(a);
        b_all.extend(b);
    }
    // a = target side, b = query side; map back to (pre, post).
    if target_is_pre {
        (a_all, b_all)
    } else {
        (b_all, a_all)
    }
}

#[inline]
fn to_local(r_t: &Mat3, p_t: Vec3, r_q: &Mat3, p_q: Vec3, x: Vec3) -> Vec3 {
    let w = matvec(r_q, x);
    let w = [w[0] + p_q[0] - p_t[0], w[1] + p_q[1] - p_t[1], w[2] + p_q[2] - p_t[2]];
    matvec_t(r_t, w)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::geom::segment_segment_dist2;

    const ID: Mat3 = [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]];

    fn seg(p: Vec3, q: Vec3, r: f64, b: i64, pt: i64) -> Segment {
        Segment {
            p,
            q,
            radius: r,
            branch: b,
            point: pt,
        }
    }

    // Brute-force reference over the world-space segments of every cell pair.
    fn brute(
        library: &[Vec<Segment>],
        pre: &Instances,
        post: &Instances,
        contact: f64,
    ) -> std::collections::HashSet<(i64, i64, i64, i64, i64, i64)> {
        let world = |inst: &Instances, ci: usize| -> Vec<Segment> {
            library[inst.morpho[ci] as usize]
                .iter()
                .map(|s| Segment {
                    p: add(matvec(&inst.rot[ci], s.p), inst.pos[ci]),
                    q: add(matvec(&inst.rot[ci], s.q), inst.pos[ci]),
                    radius: s.radius,
                    branch: s.branch,
                    point: s.point,
                })
                .collect()
        };
        let mut set = std::collections::HashSet::new();
        for pi in 0..pre.len() {
            for poi in 0..post.len() {
                for a in &world(pre, pi) {
                    for b in &world(post, poi) {
                        let thr = a.radius + b.radius + contact;
                        if segment_segment_dist2(a.p, a.q, b.p, b.q) <= thr * thr {
                            set.insert((
                                pi as i64, a.branch, a.point, poi as i64, b.branch, b.point,
                            ));
                        }
                    }
                }
            }
        }
        set
    }

    fn add(a: Vec3, b: Vec3) -> Vec3 {
        [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
    }

    #[test]
    fn matches_bruteforce() {
        // Two morphologies, several instances at various positions/rotations.
        let library = vec![
            vec![
                seg([0., 0., 0.], [1., 0., 0.], 0.1, 0, 0),
                seg([1., 0., 0.], [1., 1., 0.], 0.1, 0, 1),
            ],
            vec![seg([0., 0., 0.], [0., 0., 1.], 0.1, 0, 0)],
        ];
        // 90-degree rotation about z, to exercise the transforms.
        let rz: Mat3 = [[0., -1., 0.], [1., 0., 0.], [0., 0., 1.]];
        let pre_m = [0u32, 1, 0];
        let pre_r = [ID, rz, ID];
        let pre_p = [[0., 0., 0.], [2., 0., 0.], [0.5, 0.5, 0.0]];
        let post_m = [1u32, 0];
        let post_r = [ID, ID];
        let post_p = [[2.2, 0.2, 0.0], [0.2, 0.2, 0.0]];
        let pre = Instances {
            morpho: &pre_m,
            rot: &pre_r,
            pos: &pre_p,
        };
        let post = Instances {
            morpho: &post_m,
            rot: &post_r,
            pos: &post_p,
        };
        let contact = 0.5;

        let want = brute(&library, &pre, &post, contact);
        for favor in [Favor::Pre, Favor::Post] {
            let (a, b) = connect_segments(&library, &pre, &post, contact, favor, 1.0, 0);
            assert_eq!(a.len(), b.len());
            let got: std::collections::HashSet<_> = a
                .iter()
                .zip(b.iter())
                .map(|(pa, pb)| (pa[0], pa[1], pa[2], pb[0], pb[1], pb[2]))
                .collect();
            assert_eq!(got, want, "favor mismatch");
        }
    }

    #[test]
    fn affinity_subsamples() {
        // A query cell overlapping many target cells; affinity should thin the
        // partners. One query morphology, many target instances around it.
        let library = vec![vec![seg([-2., 0., 0.], [2., 0., 0.], 0.2, 0, 0)]];
        let n_targets = 40;
        let t_m = vec![0u32; n_targets];
        let t_r = vec![ID; n_targets];
        let t_p: Vec<Vec3> = (0..n_targets).map(|i| [0.0, i as f64 * 0.1, 0.0]).collect();
        let targets = Instances {
            morpho: &t_m,
            rot: &t_r,
            pos: &t_p,
        };
        let q_m = [0u32];
        let q_r = [ID];
        let q_p = [[0.0, 2.0, 0.0]];
        let queries = Instances {
            morpho: &q_m,
            rot: &q_r,
            pos: &q_p,
        };
        let full =
            connect_segments(&library, &queries, &targets, 5.0, Favor::Post, 1.0, 0)
                .0
                .len();
        let half =
            connect_segments(&library, &queries, &targets, 5.0, Favor::Post, 0.5, 0)
                .0
                .len();
        let none =
            connect_segments(&library, &queries, &targets, 5.0, Favor::Post, 0.0, 0)
                .0
                .len();
        assert!(full > 10, "expected many full-affinity contacts, got {full}");
        assert_eq!(none, 0, "affinity 0 should make no connections");
        assert!(half < full && half > 0, "affinity 0.5 got {half} of {full}");
        // Reproducible for a fixed seed.
        let half2 =
            connect_segments(&library, &queries, &targets, 5.0, Favor::Post, 0.5, 0)
                .0
                .len();
        assert_eq!(half, half2, "affinity subsampling must be reproducible");
    }
}
