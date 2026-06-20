"""Native (Rust) numerical kernels for the BSB.

The heavy lifting lives in the compiled extension :mod:`bsb_native._native`,
built from Rust. This package re-exports its public kernels. It has no dependency
on ``bsb-core``; it is a standalone numeric library (numpy in, numpy out).
"""

from ._native import SegmentTree, poisson_disk

__all__ = ["SegmentTree", "poisson_disk"]
