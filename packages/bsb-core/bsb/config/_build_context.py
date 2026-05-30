"""
Build-time context for configuration construction.

A :class:`BuildContext` is set on a :class:`~contextvars.ContextVar` while a
configuration tree is being built and cleared once it finalizes. Code running
underneath the build (validators, ``required=`` callables, ...) can retrieve it
via :func:`get_config_build_context` to share state across nodes without
threading it through every constructor.

The context is a namespace: callers attach packages' shared objects under a
sub-namespace, e.g. ``ctx.bsb_nest.kernel = proxy``. Resources that need
teardown register a callback via :meth:`BuildContext.add_cleanup`; callbacks
run in LIFO order when the build exits.
"""

import contextlib
from contextvars import ContextVar
from types import SimpleNamespace


class BuildContext(SimpleNamespace):
    """Per-build shared state, accessed via attribute-style sub-namespaces.

    Reading a top-level attribute that hasn't been set yet auto-creates an
    empty ``SimpleNamespace`` sub-namespace, so callers can write
    ``ctx.bsb_nest.kernel = proxy`` without manually setting up
    ``ctx.bsb_nest`` first. Leaf reads (``ctx.bsb_nest.kernel``) are NOT
    auto-vivified — callers must use ``ns.__dict__.get(...)`` or
    ``getattr(ns, ..., default)`` for missing-leaf checks.
    """

    def __init__(self):
        super().__init__()
        object.__setattr__(self, "_cleanup_callbacks", [])

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        ns = SimpleNamespace()
        object.__setattr__(self, name, ns)
        return ns

    def add_cleanup(self, callback):
        """Register a zero-arg callable to run when the build context exits."""
        self._cleanup_callbacks.append(callback)

    def _run_cleanups(self):
        while self._cleanup_callbacks:
            cb = self._cleanup_callbacks.pop()
            # A cleanup failure must not prevent later cleanups from running.
            with contextlib.suppress(Exception):
                cb()


_build_context_var: ContextVar = ContextVar("bsb_build_context", default=None)


def set_config_build_context(ctx):
    """Set the active build context. Returns the reset token."""
    return _build_context_var.set(ctx)


def get_config_build_context():
    """Return the active :class:`BuildContext` or ``None`` outside a build."""
    return _build_context_var.get()


@contextlib.contextmanager
def build_context():
    """Context manager that owns the lifecycle of a :class:`BuildContext`."""
    ctx = BuildContext()
    token = set_config_build_context(ctx)
    try:
        yield ctx
    finally:
        try:
            ctx._run_cleanups()
        finally:
            _build_context_var.reset(token)
