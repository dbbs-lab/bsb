import sys
import unittest
import warnings
from unittest.mock import patch

from bsb import RequirementError
from bsb.config import build_context, get_config_build_context

from bsb_nest import get_nest_kernel_proxy
from bsb_nest._kernel_proxy import _NestKernel


class TestKernelProxyLifecycle(unittest.TestCase):
    def test_returns_none_outside_build(self):
        self.assertIsNone(get_nest_kernel_proxy())

    def test_registers_under_bsb_nest_namespace_and_cleans_up(self):
        manager_shutdowns = []

        class _StubManager:
            def __init__(self):
                self._kernel = object()

            def start(self):
                pass

            def kernel(self):
                return self._kernel

            def shutdown(self):
                manager_shutdowns.append(self)

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=lambda: _StubManager(),
        ):
            with build_context() as ctx:
                proxy = get_nest_kernel_proxy()
                self.assertIs(proxy, ctx.bsb_nest.kernel)
                # Repeated calls reuse the same proxy.
                self.assertIs(get_nest_kernel_proxy(), proxy)
                self.assertEqual(manager_shutdowns, [])
            self.assertEqual(len(manager_shutdowns), 1)


class TestDelayRequiredChecker(unittest.TestCase):
    """Exercises the checker via the real (in-process) ``_NestKernel`` helper.

    These tests stand in for the subprocess by patching ``_start_kernel_manager``
    so the proxy is just a ``_NestKernel`` instance — sidesteps subprocess
    startup cost in unit tests while exercising the same code paths the proxy
    would.
    """

    @classmethod
    def setUpClass(cls):
        try:
            import nest  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("NEST is not installed")

    def _make_stub_manager(self):
        kernel = _NestKernel()

        class _StubManager:
            def start(self):
                pass

            def kernel(self):
                return kernel

            def shutdown(self):
                pass

        return _StubManager()

    def _build_synapse(self, *, model, delay=None):
        from bsb_nest.connection import NestSynapseSettings

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=self._make_stub_manager,
        ):
            with build_context():
                kwargs = {"model": model}
                if delay is not None:
                    kwargs["delay"] = delay
                return NestSynapseSettings(kwargs)

    def test_static_synapse_requires_delay(self):
        from bsb_nest.connection import NestSynapseSettings

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=self._make_stub_manager,
        ):
            with build_context():
                with self.assertRaises(RequirementError):
                    NestSynapseSettings(
                        {"model": "static_synapse", "weight": 1.0},
                    )

    def test_gap_junction_does_not_require_delay(self):
        # gap_junction is a real NEST synapse model with has_delay=False.
        from bsb_nest.connection import NestSynapseSettings

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=self._make_stub_manager,
        ):
            with build_context():
                # No delay supplied — must not raise.
                NestSynapseSettings(
                    {"model": "gap_junction", "weight": 1.0},
                )

    def test_unknown_synapse_warns_and_falls_back(self):
        from bsb_nest.connection import NestSynapseSettings
        from bsb_nest.exceptions import KernelWarning

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=self._make_stub_manager,
        ):
            with build_context():
                with warnings.catch_warnings(record=True) as log:
                    warnings.simplefilter("always", KernelWarning)
                    # Unknown model — checker must warn and treat delay as optional,
                    # so building without delay succeeds.
                    NestSynapseSettings(
                        {"model": "definitely_not_a_real_model", "weight": 1.0},
                    )
                self.assertTrue(
                    any(issubclass(w.category, KernelWarning) for w in log),
                    f"Expected a KernelWarning, got: {[w.message for w in log]}",
                )

    def test_no_context_warns_and_falls_back(self):
        from bsb_nest.connection import _is_delay_required
        from bsb_nest.exceptions import KernelWarning

        with warnings.catch_warnings(record=True) as log:
            warnings.simplefilter("always", KernelWarning)
            # Calling outside a build context — no proxy available.
            result = _is_delay_required({"model": "static_synapse"})
        self.assertFalse(result)
        self.assertTrue(
            any(issubclass(w.category, KernelWarning) for w in log),
            f"Expected a KernelWarning, got: {[w.message for w in log]}",
        )

    def test_proxy_failure_warns_and_falls_back(self):
        from bsb_nest.connection import _is_delay_required
        from bsb_nest.exceptions import KernelWarning

        def boom():
            raise RuntimeError("kernel unreachable")

        with patch(
            "bsb_nest._kernel_proxy._start_kernel_manager",
            side_effect=boom,
        ):
            with build_context():
                with warnings.catch_warnings(record=True) as log:
                    warnings.simplefilter("always", KernelWarning)
                    result = _is_delay_required({"model": "static_synapse"})
        self.assertFalse(result)
        self.assertTrue(
            any(issubclass(w.category, KernelWarning) for w in log),
            f"Expected a KernelWarning, got: {[w.message for w in log]}",
        )


class TestImportingBsbNestDoesNotImportNest(unittest.TestCase):
    """`import bsb_nest` must not pull NEST into the user's process."""

    def test_nest_absent_after_import(self):
        # Note: this test only proves a regression if NEST has not been
        # imported earlier in the same Python process. Other tests in this
        # file do `import nest`, so we re-check by spawning a subprocess.
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import bsb_nest, sys;"
                " assert 'nest' not in sys.modules, sorted(sys.modules)",
            ],
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            result.returncode,
            0,
            f"stdout={result.stdout!r}\nstderr={result.stderr!r}",
        )


if __name__ == "__main__":
    unittest.main()
