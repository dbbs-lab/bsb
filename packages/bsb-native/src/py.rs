//! PyO3 bindings exposing the pure-Rust kernels to Python. Compiled only under
//! the `python` feature (enabled by maturin); the algorithm core stays free of
//! any Python dependency so it can be unit-tested with `cargo test`.

use numpy::ndarray::Array2;
use numpy::{IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2};
use pyo3::prelude::*;

use crate::bvh::{Segment, SegmentTree as CoreTree};
use crate::poisson::poisson_disk as core_poisson;

/// Sample points in the box `[lo, hi]` no closer than `min_distance` to each
/// other or to any `fixed` point, returning an `(N, 3)` float64 array.
///
/// `fixed` (shape `(M, 3)`) are already-placed neighbours (e.g. a cross-chunk
/// halo); they constrain but are not returned. `max_count` caps the output;
/// `None` fills to saturation. `seed` makes the result reproducible.
#[pyfunction]
#[pyo3(signature = (lo, hi, min_distance, k = 30, fixed = None, max_count = None, seed = 0))]
fn poisson_disk<'py>(
    py: Python<'py>,
    lo: [f64; 3],
    hi: [f64; 3],
    min_distance: f64,
    k: usize,
    fixed: Option<PyReadonlyArray2<'py, f64>>,
    max_count: Option<usize>,
    seed: u64,
) -> Bound<'py, PyArray2<f64>> {
    let fixed_vec: Vec<[f64; 3]> = match &fixed {
        Some(arr) => arr
            .as_array()
            .outer_iter()
            .map(|row| [row[0], row[1], row[2]])
            .collect(),
        None => Vec::new(),
    };
    let pts = core_poisson(lo, hi, min_distance, k, &fixed_vec, max_count, seed);
    let n = pts.len();
    let mut flat = Vec::with_capacity(n * 3);
    for p in &pts {
        flat.extend_from_slice(p);
    }
    Array2::from_shape_vec((n, 3), flat)
        .expect("flat buffer is N*3")
        .into_pyarray_bound(py)
}

fn build_segments(
    p: &PyReadonlyArray2<f64>,
    q: &PyReadonlyArray2<f64>,
    radius: &PyReadonlyArray1<f64>,
    branch: &PyReadonlyArray1<i64>,
    point: &PyReadonlyArray1<i64>,
) -> Vec<Segment> {
    let p = p.as_array();
    let q = q.as_array();
    let radius = radius.as_array();
    let branch = branch.as_array();
    let point = point.as_array();
    let n = p.shape()[0];
    (0..n)
        .map(|i| Segment {
            p: [p[[i, 0]], p[[i, 1]], p[[i, 2]]],
            q: [q[[i, 0]], q[[i, 1]], q[[i, 2]]],
            radius: radius[i],
            branch: branch[i],
            point: point[i],
        })
        .collect()
}

/// A per-morphology segment BVH (the "BLAS"): build once over one morphology's
/// segments in its local frame, then query it with other cells' segments
/// transformed into that frame.
#[pyclass]
struct SegmentTree {
    inner: CoreTree,
}

#[pymethods]
impl SegmentTree {
    /// Build from a morphology's segments. All arrays are length `M` (one per
    /// segment): `seg_p`/`seg_q` are the `(M, 3)` endpoints in the morphology's
    /// local frame, `seg_radius` the per-segment radius, and
    /// `seg_branch`/`seg_point` the location reported on a contact.
    #[new]
    fn new(
        seg_p: PyReadonlyArray2<f64>,
        seg_q: PyReadonlyArray2<f64>,
        seg_radius: PyReadonlyArray1<f64>,
        seg_branch: PyReadonlyArray1<i64>,
        seg_point: PyReadonlyArray1<i64>,
    ) -> Self {
        let segs = build_segments(&seg_p, &seg_q, &seg_radius, &seg_branch, &seg_point);
        SegmentTree {
            inner: CoreTree::build(segs),
        }
    }

    fn __len__(&self) -> usize {
        self.inner.len()
    }

    /// Query the tree with a batch of segments (already transformed into the
    /// tree's local frame). Returns two `(K, 3)` int64 arrays of `[cell, branch,
    /// point]` location triples: the first on the tree (target) side, the second
    /// on the query (candidate) side, one row per contact within `contact`.
    #[pyo3(signature = (q_p, q_q, q_radius, q_branch, q_point, q_cell, target_cell, contact))]
    #[allow(clippy::too_many_arguments)]
    fn query_batch<'py>(
        &self,
        py: Python<'py>,
        q_p: PyReadonlyArray2<f64>,
        q_q: PyReadonlyArray2<f64>,
        q_radius: PyReadonlyArray1<f64>,
        q_branch: PyReadonlyArray1<i64>,
        q_point: PyReadonlyArray1<i64>,
        q_cell: PyReadonlyArray1<i64>,
        target_cell: i64,
        contact: f64,
    ) -> (Bound<'py, PyArray2<i64>>, Bound<'py, PyArray2<i64>>) {
        let queries = build_segments(&q_p, &q_q, &q_radius, &q_branch, &q_point);
        let q_cell = q_cell.as_array();
        let pairs = self.inner.query_batch(&queries, contact);

        let k = pairs.len();
        let mut a = Vec::with_capacity(k * 3);
        let mut b = Vec::with_capacity(k * 3);
        for (ti, qi) in pairs {
            let (branch, point) = self.inner.location(ti);
            a.extend_from_slice(&[target_cell, branch, point]);
            b.extend_from_slice(&[q_cell[qi], queries[qi].branch, queries[qi].point]);
        }
        let a = Array2::from_shape_vec((k, 3), a).expect("flat buffer is K*3");
        let b = Array2::from_shape_vec((k, 3), b).expect("flat buffer is K*3");
        (a.into_pyarray_bound(py), b.into_pyarray_bound(py))
    }
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(poisson_disk, m)?)?;
    m.add_class::<SegmentTree>()?;
    Ok(())
}
