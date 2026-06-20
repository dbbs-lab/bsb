//! Geometric primitives: 3D vectors, axis-aligned bounding boxes, and the exact
//! segment-to-segment (capsule) distance test that is the connectivity criterion.

pub type Vec3 = [f64; 3];

#[inline]
pub fn sub(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] - b[0], a[1] - b[1], a[2] - b[2]]
}
#[inline]
pub fn add(a: Vec3, b: Vec3) -> Vec3 {
    [a[0] + b[0], a[1] + b[1], a[2] + b[2]]
}
#[inline]
pub fn scale(a: Vec3, s: f64) -> Vec3 {
    [a[0] * s, a[1] * s, a[2] * s]
}
#[inline]
pub fn dot(a: Vec3, b: Vec3) -> f64 {
    a[0] * b[0] + a[1] * b[1] + a[2] * b[2]
}
#[inline]
pub fn dist2(a: Vec3, b: Vec3) -> f64 {
    let d = sub(a, b);
    dot(d, d)
}

/// Squared distance between segments `[p1, q1]` and `[p2, q2]`.
///
/// Closed-form clamped closest-point solve, after Ericson, *Real-Time Collision
/// Detection*, `ClosestPtSegmentSegment`. Degenerate (zero-length) segments are
/// handled, so points (p == q) work as a special case.
pub fn segment_segment_dist2(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> f64 {
    const EPS: f64 = 1e-12;
    let d1 = sub(q1, p1);
    let d2 = sub(q2, p2);
    let r = sub(p1, p2);
    let a = dot(d1, d1); // squared length of segment 1
    let e = dot(d2, d2); // squared length of segment 2
    let f = dot(d2, r);

    let (s, t);
    if a <= EPS && e <= EPS {
        return dist2(p1, p2); // both segments are points
    }
    if a <= EPS {
        s = 0.0;
        t = (f / e).clamp(0.0, 1.0);
    } else {
        let c = dot(d1, r);
        if e <= EPS {
            t = 0.0;
            s = (-c / a).clamp(0.0, 1.0);
        } else {
            let b = dot(d1, d2);
            let denom = a * e - b * b;
            let s0 = if denom > EPS {
                ((b * f - c * e) / denom).clamp(0.0, 1.0)
            } else {
                0.0 // parallel: pick an arbitrary point on segment 1
            };
            let t0 = (b * s0 + f) / e;
            if t0 < 0.0 {
                t = 0.0;
                s = (-c / a).clamp(0.0, 1.0);
            } else if t0 > 1.0 {
                t = 1.0;
                s = ((b - c) / a).clamp(0.0, 1.0);
            } else {
                t = t0;
                s = s0;
            }
        }
    }
    let c1 = add(p1, scale(d1, s));
    let c2 = add(p2, scale(d2, t));
    dist2(c1, c2)
}

/// Axis-aligned bounding box.
#[derive(Clone, Copy, Debug)]
pub struct Aabb {
    pub min: Vec3,
    pub max: Vec3,
}

impl Aabb {
    pub fn empty() -> Self {
        Aabb {
            min: [f64::INFINITY; 3],
            max: [f64::NEG_INFINITY; 3],
        }
    }

    /// Box around a segment, inflated by `pad` (e.g. the segment radius).
    pub fn from_segment(p: Vec3, q: Vec3, pad: f64) -> Self {
        let mut a = Aabb::empty();
        a.expand_point(p);
        a.expand_point(q);
        a.pad(pad);
        a
    }

    #[inline]
    pub fn expand_point(&mut self, p: Vec3) {
        for k in 0..3 {
            if p[k] < self.min[k] {
                self.min[k] = p[k];
            }
            if p[k] > self.max[k] {
                self.max[k] = p[k];
            }
        }
    }

    #[inline]
    pub fn expand(&mut self, o: &Aabb) {
        for k in 0..3 {
            if o.min[k] < self.min[k] {
                self.min[k] = o.min[k];
            }
            if o.max[k] > self.max[k] {
                self.max[k] = o.max[k];
            }
        }
    }

    #[inline]
    pub fn pad(&mut self, r: f64) {
        for k in 0..3 {
            self.min[k] -= r;
            self.max[k] += r;
        }
    }

    #[inline]
    pub fn centroid(&self) -> Vec3 {
        [
            (self.min[0] + self.max[0]) * 0.5,
            (self.min[1] + self.max[1]) * 0.5,
            (self.min[2] + self.max[2]) * 0.5,
        ]
    }

    #[inline]
    pub fn overlaps(&self, o: &Aabb) -> bool {
        self.min[0] <= o.max[0]
            && self.max[0] >= o.min[0]
            && self.min[1] <= o.max[1]
            && self.max[1] >= o.min[1]
            && self.min[2] <= o.max[2]
            && self.max[2] >= o.min[2]
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn d(p1: Vec3, q1: Vec3, p2: Vec3, q2: Vec3) -> f64 {
        segment_segment_dist2(p1, q1, p2, q2).sqrt()
    }

    #[test]
    fn parallel_segments() {
        // Two unit segments along x, 3 apart in y.
        let got = d([0., 0., 0.], [1., 0., 0.], [0., 3., 0.], [1., 3., 0.]);
        assert!((got - 3.0).abs() < 1e-9, "got {got}");
    }

    #[test]
    fn crossing_skew_segments() {
        // Perpendicular skew lines offset by 2 in z: closest distance is 2.
        let got = d([-1., 0., 0.], [1., 0., 0.], [0., -1., 2.], [0., 1., 2.]);
        assert!((got - 2.0).abs() < 1e-9, "got {got}");
    }

    #[test]
    fn endpoint_to_endpoint() {
        let got = d([0., 0., 0.], [1., 0., 0.], [4., 0., 0.], [5., 0., 0.]);
        assert!((got - 3.0).abs() < 1e-9, "got {got}");
    }

    #[test]
    fn point_segments() {
        // Two degenerate (point) segments.
        let got = d([0., 0., 0.], [0., 0., 0.], [3., 4., 0.], [3., 4., 0.]);
        assert!((got - 5.0).abs() < 1e-9, "got {got}");
    }

    #[test]
    fn aabb_overlap() {
        let a = Aabb::from_segment([0., 0., 0.], [1., 1., 1.], 0.0);
        let b = Aabb::from_segment([0.5, 0.5, 0.5], [2., 2., 2.], 0.0);
        let c = Aabb::from_segment([5., 5., 5.], [6., 6., 6.], 0.0);
        assert!(a.overlaps(&b));
        assert!(!a.overlaps(&c));
    }
}
