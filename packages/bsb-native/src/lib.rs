//! Native numerical kernels for the BSB.
//!
//! The algorithm core (`geom`, `bvh`, `poisson`) is pure Rust with no Python
//! dependency, so it can be unit-tested with `cargo test`. The `py` module
//! holds the PyO3 bindings and only compiles under the `python` feature, which
//! maturin enables when building the extension wheel.

pub mod bvh;
pub mod geom;
pub mod poisson;
pub mod scene;

#[cfg(feature = "python")]
mod py;
