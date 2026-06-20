//! PyO3 bindings exposing the pure-Rust kernels to Python. Compiled only under
//! the `python` feature (enabled by maturin); the algorithm core stays free of
//! any Python dependency so it can be unit-tested with `cargo test`.

use numpy::ndarray::Array2;
use numpy::{
    IntoPyArray, PyArray2, PyReadonlyArray1, PyReadonlyArray2, PyReadonlyArray3,
};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use crate::bvh::Segment;
use crate::geom::{Mat3, Vec3};
use crate::poisson::poisson_disk as core_poisson;
use crate::scene::{connect_segments as core_connect, Favor, Instances};

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
    let pts = py.allow_threads(|| {
        core_poisson(lo, hi, min_distance, k, &fixed_vec, max_count, seed)
    });
    let n = pts.len();
    let mut flat = Vec::with_capacity(n * 3);
    for p in &pts {
        flat.extend_from_slice(p);
    }
    Array2::from_shape_vec((n, 3), flat)
        .expect("flat buffer is N*3")
        .into_pyarray_bound(py)
}

fn build_library(
    p: &PyReadonlyArray2<f64>,
    q: &PyReadonlyArray2<f64>,
    radius: &PyReadonlyArray1<f64>,
    branch: &PyReadonlyArray1<i64>,
    point: &PyReadonlyArray1<i64>,
    offsets: &PyReadonlyArray1<i64>,
) -> Vec<Vec<Segment>> {
    let p = p.as_array();
    let q = q.as_array();
    let radius = radius.as_array();
    let branch = branch.as_array();
    let point = point.as_array();
    let offsets = offsets.as_array();
    let m = offsets.len().saturating_sub(1);
    (0..m)
        .map(|mi| {
            let s = offsets[mi] as usize;
            let e = offsets[mi + 1] as usize;
            (s..e)
                .map(|i| Segment {
                    p: [p[[i, 0]], p[[i, 1]], p[[i, 2]]],
                    q: [q[[i, 0]], q[[i, 1]], q[[i, 2]]],
                    radius: radius[i],
                    branch: branch[i],
                    point: point[i],
                })
                .collect()
        })
        .collect()
}

fn build_instances(
    morpho: &PyReadonlyArray1<i64>,
    rot: &PyReadonlyArray3<f64>,
    pos: &PyReadonlyArray2<f64>,
) -> (Vec<u32>, Vec<Mat3>, Vec<Vec3>) {
    let morpho = morpho.as_array();
    let rot = rot.as_array();
    let pos = pos.as_array();
    let n = morpho.len();
    let m: Vec<u32> = (0..n).map(|i| morpho[i] as u32).collect();
    let r: Vec<Mat3> = (0..n)
        .map(|i| {
            [
                [rot[[i, 0, 0]], rot[[i, 0, 1]], rot[[i, 0, 2]]],
                [rot[[i, 1, 0]], rot[[i, 1, 1]], rot[[i, 1, 2]]],
                [rot[[i, 2, 0]], rot[[i, 2, 1]], rot[[i, 2, 2]]],
            ]
        })
        .collect();
    let p: Vec<Vec3> = (0..n).map(|i| [pos[[i, 0]], pos[[i, 1]], pos[[i, 2]]]).collect();
    (m, r, p)
}

fn locs_to_array<'py>(py: Python<'py>, locs: &[[i64; 3]]) -> Bound<'py, PyArray2<i64>> {
    let k = locs.len();
    let mut flat = Vec::with_capacity(k * 3);
    for l in locs {
        flat.extend_from_slice(l);
    }
    Array2::from_shape_vec((k, 3), flat)
        .expect("flat buffer is K*3")
        .into_pyarray_bound(py)
}

/// Connect two cell populations by morphology-segment proximity.
///
/// The morphology library is passed as flat per-segment arrays plus `lib_offsets`
/// (length `M+1`) delimiting each morphology's segment range. Each population is
/// given as instances: a per-cell `morpho` index into the library, a per-cell
/// `(N, 3, 3)` rotation matrix, and a per-cell `(N, 3)` position. `favor` ("pre"
/// or "post") selects which side builds the trees. Returns `(pre_locs,
/// post_locs)`, each an `(K, 3)` int64 array of `[cell, branch, point]` triples
/// aligned row-by-row, one per contact.
#[pyfunction]
#[pyo3(signature = (
    lib_p, lib_q, lib_radius, lib_branch, lib_point, lib_offsets,
    pre_morpho, pre_rot, pre_pos, post_morpho, post_rot, post_pos,
    contact, favor = "pre", affinity = 1.0, seed = 0
))]
#[allow(clippy::too_many_arguments)]
fn connect_segments<'py>(
    py: Python<'py>,
    lib_p: PyReadonlyArray2<f64>,
    lib_q: PyReadonlyArray2<f64>,
    lib_radius: PyReadonlyArray1<f64>,
    lib_branch: PyReadonlyArray1<i64>,
    lib_point: PyReadonlyArray1<i64>,
    lib_offsets: PyReadonlyArray1<i64>,
    pre_morpho: PyReadonlyArray1<i64>,
    pre_rot: PyReadonlyArray3<f64>,
    pre_pos: PyReadonlyArray2<f64>,
    post_morpho: PyReadonlyArray1<i64>,
    post_rot: PyReadonlyArray3<f64>,
    post_pos: PyReadonlyArray2<f64>,
    contact: f64,
    favor: &str,
    affinity: f64,
    seed: u64,
) -> PyResult<(Bound<'py, PyArray2<i64>>, Bound<'py, PyArray2<i64>>)> {
    let favor = match favor {
        "pre" => Favor::Pre,
        "post" => Favor::Post,
        other => {
            return Err(PyValueError::new_err(format!(
                "favor must be 'pre' or 'post', got '{other}'"
            )))
        }
    };
    let library =
        build_library(&lib_p, &lib_q, &lib_radius, &lib_branch, &lib_point, &lib_offsets);
    let (pre_m, pre_r, pre_p) = build_instances(&pre_morpho, &pre_rot, &pre_pos);
    let (post_m, post_r, post_p) = build_instances(&post_morpho, &post_rot, &post_pos);
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
    // Release the GIL for the heavy, Python-free computation.
    let (a, b) = py.allow_threads(|| {
        core_connect(&library, &pre, &post, contact, favor, affinity, seed)
    });
    Ok((locs_to_array(py, &a), locs_to_array(py, &b)))
}

#[pymodule]
fn _native(m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(poisson_disk, m)?)?;
    m.add_function(wrap_pyfunction!(connect_segments, m)?)?;
    Ok(())
}
