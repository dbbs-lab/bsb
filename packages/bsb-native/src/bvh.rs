//! A bounding-volume hierarchy over line segments, used as the per-morphology
//! acceleration structure (the "BLAS"). Build once over one morphology's
//! segments in its local frame; query it with another cell's segments,
//! transformed into this frame, to find segment pairs within contact distance.
//!
//! The broad phase prunes with padded AABBs; every surviving pair gets the exact
//! [`geom::segment_segment_dist2`] capsule test, so reported hits are exact.

use crate::geom::{segment_segment_dist2, Aabb, Vec3};
use rayon::prelude::*;

/// One indexed segment with its radius and the location it reports on a hit.
#[derive(Clone, Copy)]
pub struct Segment {
    pub p: Vec3,
    pub q: Vec3,
    pub radius: f64,
    /// Morphology branch id reported for this segment on a contact.
    pub branch: i64,
    /// Point id within the branch reported for this segment on a contact.
    pub point: i64,
}

struct Node {
    bbox: Aabb,
    /// Child node indices for an internal node. `left == usize::MAX` marks a leaf.
    /// Children are not contiguous in `nodes` (the left subtree is built first),
    /// so both indices are stored explicitly.
    left: usize,
    right: usize,
    /// Leaf primitive range into `order` (`[first, first+count)`).
    first: usize,
    count: usize,
}

pub struct SegmentTree {
    segs: Vec<Segment>,
    order: Vec<usize>,
    nodes: Vec<Node>,
    max_radius: f64,
}

const LEAF_SIZE: usize = 4;

impl SegmentTree {
    pub fn build(segs: Vec<Segment>) -> Self {
        let n = segs.len();
        let max_radius = segs.iter().fold(0.0_f64, |m, s| m.max(s.radius));
        let mut order: Vec<usize> = (0..n).collect();
        let mut nodes: Vec<Node> = Vec::with_capacity(2 * n.max(1));
        if n > 0 {
            build_recursive(&segs, &mut order, &mut nodes, 0, n);
        }
        SegmentTree {
            segs,
            order,
            nodes,
            max_radius,
        }
    }

    pub fn len(&self) -> usize {
        self.segs.len()
    }
    pub fn is_empty(&self) -> bool {
        self.segs.is_empty()
    }

    /// The `(branch, point)` location reported for tree segment `seg_index`
    /// (the first element of a `query_batch` pair).
    pub fn location(&self, seg_index: usize) -> (i64, i64) {
        let s = &self.segs[seg_index];
        (s.branch, s.point)
    }

    /// Push every tree segment within `contact` of capsule `[p, q]` (radius `r`)
    /// onto `out` as `(tree_segment_index, squared_distance)`.
    fn query_into(&self, p: Vec3, q: Vec3, r: f64, contact: f64, out: &mut Vec<usize>) {
        if self.nodes.is_empty() {
            return;
        }
        // Broad-phase query box: the query capsule padded so it can reach any
        // tree capsule within `contact`. Tree leaf boxes are padded by each
        // segment's own radius at build time, so padding the query by
        // (r + contact + max_radius) makes box-overlap a necessary condition
        // for the exact test to pass.
        let mut qbox = Aabb::from_segment(p, q, r + contact + self.max_radius);
        let mut stack = [0usize; 64];
        let mut sp = 0usize;
        stack[sp] = 0;
        sp += 1;
        while sp > 0 {
            sp -= 1;
            let ni = stack[sp];
            let node = &self.nodes[ni];
            if !node.bbox.overlaps(&qbox) {
                continue;
            }
            if node.left == usize::MAX {
                for &oi in &self.order[node.first..node.first + node.count] {
                    let s = &self.segs[oi];
                    let thr = r + s.radius + contact;
                    if segment_segment_dist2(p, q, s.p, s.q) <= thr * thr {
                        out.push(oi);
                    }
                }
            } else {
                let (l, r2) = (node.left, node.right);
                // Guard against pathological depth; LEAF_SIZE keeps trees shallow.
                if sp + 2 <= stack.len() {
                    stack[sp] = l;
                    sp += 1;
                    stack[sp] = r2;
                    sp += 1;
                } else {
                    // Fallback: scan this subtree's leaves linearly (rare).
                    self.scan_subtree(ni, &mut qbox, p, q, r, contact, out);
                }
            }
        }
    }

    fn scan_subtree(
        &self,
        ni: usize,
        qbox: &mut Aabb,
        p: Vec3,
        q: Vec3,
        r: f64,
        contact: f64,
        out: &mut Vec<usize>,
    ) {
        let node = &self.nodes[ni];
        if !node.bbox.overlaps(qbox) {
            return;
        }
        if node.left == usize::MAX {
            for &oi in &self.order[node.first..node.first + node.count] {
                let s = &self.segs[oi];
                let thr = r + s.radius + contact;
                if segment_segment_dist2(p, q, s.p, s.q) <= thr * thr {
                    out.push(oi);
                }
            }
        } else {
            let (l, r2) = (node.left, node.right);
            self.scan_subtree(l, qbox, p, q, r, contact, out);
            self.scan_subtree(r2, qbox, p, q, r, contact, out);
        }
    }

    /// Match a batch of query segments against the tree in parallel.
    ///
    /// Returns, for every contact, a pair `(tree_segment_index,
    /// query_segment_index)`. Use the stored [`Segment::branch`]/[`Segment::point`]
    /// (tree side) and the caller's per-query metadata (query side) to build the
    /// `[cell, branch, point]` location triples.
    pub fn query_batch(&self, queries: &[Segment], contact: f64) -> Vec<(usize, usize)> {
        queries
            .par_iter()
            .enumerate()
            .map(|(qi, s)| {
                let mut hits = Vec::new();
                self.query_into(s.p, s.q, s.radius, contact, &mut hits);
                hits.into_iter().map(move |ti| (ti, qi)).collect::<Vec<_>>()
            })
            .flatten()
            .collect()
    }

    /// Convenience for the single-query, non-parallel path (and tests).
    pub fn query(&self, p: Vec3, q: Vec3, r: f64, contact: f64) -> Vec<usize> {
        let mut out = Vec::new();
        self.query_into(p, q, r, contact, &mut out);
        out
    }
}

fn build_recursive(
    segs: &[Segment],
    order: &mut [usize],
    nodes: &mut Vec<Node>,
    first: usize,
    count: usize,
) -> usize {
    // Compute this node's box (segments padded by their radius) and the
    // centroid bounds used to choose a split axis.
    let mut bbox = Aabb::empty();
    let mut cbox = Aabb::empty();
    for &oi in &order[first..first + count] {
        let s = &segs[oi];
        let sb = Aabb::from_segment(s.p, s.q, s.radius);
        bbox.expand(&sb);
        cbox.expand_point(sb.centroid());
    }

    let node_index = nodes.len();
    nodes.push(Node {
        bbox,
        left: usize::MAX,
        right: usize::MAX,
        first,
        count,
    });

    if count <= LEAF_SIZE {
        return node_index;
    }

    // Split on the longest centroid axis at the median.
    let extent = [
        cbox.max[0] - cbox.min[0],
        cbox.max[1] - cbox.min[1],
        cbox.max[2] - cbox.min[2],
    ];
    let axis = if extent[0] >= extent[1] && extent[0] >= extent[2] {
        0
    } else if extent[1] >= extent[2] {
        1
    } else {
        2
    };
    if extent[axis] <= 0.0 {
        return node_index; // all centroids coincide; keep as a leaf
    }

    let slice = &mut order[first..first + count];
    let mid = count / 2;
    slice.select_nth_unstable_by(mid, |&a, &b| {
        let ca = Aabb::from_segment(segs[a].p, segs[a].q, segs[a].radius).centroid()[axis];
        let cb = Aabb::from_segment(segs[b].p, segs[b].q, segs[b].radius).centroid()[axis];
        ca.partial_cmp(&cb).unwrap_or(std::cmp::Ordering::Equal)
    });

    let left = build_recursive(segs, order, nodes, first, mid);
    let right = build_recursive(segs, order, nodes, first + mid, count - mid);
    nodes[node_index].left = left;
    nodes[node_index].right = right;
    node_index
}

#[cfg(test)]
mod tests {
    use super::*;

    fn seg(p: Vec3, q: Vec3, r: f64, b: i64, pt: i64) -> Segment {
        Segment {
            p,
            q,
            radius: r,
            branch: b,
            point: pt,
        }
    }

    /// Brute-force reference: every tree-vs-query pair within contact.
    fn brute(tree: &[Segment], queries: &[Segment], contact: f64) -> Vec<(usize, usize)> {
        let mut v = Vec::new();
        for (ti, t) in tree.iter().enumerate() {
            for (qi, q) in queries.iter().enumerate() {
                let thr = t.radius + q.radius + contact;
                if segment_segment_dist2(t.p, t.q, q.p, q.q) <= thr * thr {
                    v.push((ti, qi));
                }
            }
        }
        v.sort_unstable();
        v
    }

    #[test]
    fn matches_bruteforce_on_grid() {
        // A lattice of short segments as the tree, another offset lattice as
        // queries; the BVH result must equal brute force exactly.
        let mut tree = Vec::new();
        let mut k = 0;
        for x in 0..6 {
            for y in 0..6 {
                for z in 0..6 {
                    let o = [x as f64, y as f64, z as f64];
                    tree.push(seg(o, [o[0] + 0.4, o[1], o[2]], 0.05, k, 0));
                    k += 1;
                }
            }
        }
        let mut queries = Vec::new();
        let mut k = 0;
        for x in 0..6 {
            for y in 0..6 {
                let o = [x as f64 + 0.1, y as f64 + 0.1, 2.0];
                queries.push(seg(o, [o[0], o[1] + 0.4, o[2]], 0.05, k, 0));
                k += 1;
            }
        }
        let contact = 0.3;
        let t = SegmentTree::build(tree.clone());
        let mut got = t.query_batch(&queries, contact);
        got.sort_unstable();
        let want = brute(&tree, &queries, contact);
        assert_eq!(got, want);
    }

    #[test]
    fn empty_tree_no_hits() {
        let t = SegmentTree::build(vec![]);
        assert!(t.is_empty());
        assert!(t.query([0., 0., 0.], [1., 0., 0.], 1.0, 1.0).is_empty());
    }
}
