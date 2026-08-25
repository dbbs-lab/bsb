# bsb-native

Native (Rust) numerical kernels for the [BSB](https://github.com/dbbs-lab/bsb).

This package ships a compiled extension module (`bsb_native._native`) built from
Rust with [PyO3](https://pyo3.rs) + [maturin](https://www.maturin.rs). It exposes
low-level kernels that the BSB's placement and connectivity strategies call:

- `poisson_disk(...)` — Bridson Poisson-disk sampling in a 3D box, with optional
  fixed-point constraints (for seamless cross-chunk placement) and a seed for
  reproducibility.
- `SegmentTree` — a per-morphology segment bounding-volume hierarchy (the "BLAS")
  with an exact capsule (segment-to-segment distance) query, used to find
  morphology contacts.

The package has **no dependency on `bsb-core`**: it is a pure numeric library
(numpy in, numpy out), so the kernels are reusable and independently testable.
The algorithm core is plain Rust unit-tested with `cargo test`; the PyO3 bindings
live behind the `python` cargo feature that maturin enables.

## Development

```bash
# Run the pure-Rust algorithm tests (no Python needed):
cargo test --manifest-path packages/bsb-native/Cargo.toml

# Build + install the extension into the active environment (editable):
maturin develop -m packages/bsb-native/Cargo.toml
```
