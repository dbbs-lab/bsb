import unittest
import warnings
from unittest.mock import patch

from bsb import ConfigurationError, RequirementError
from bsb.config import build_context

from bsb_nest import get_nest_kernel_proxy


def _requires_nest():
    try:
        import nest  # noqa: F401
    except ImportError as e:
        raise unittest.SkipTest("NEST is not installed") from e


class TestKernelProxyLifecycle(unittest.TestCase):
    def test_returns_none_outside_build(self):
        self.assertIsNone(get_nest_kernel_proxy())

    def test_registers_under_bsb_nest_namespace_and_cleans_up(self):
        shutdowns = []
        sentinel = object()

        def stub_connect():
            return sentinel, lambda: shutdowns.append(True)

        with patch("bsb_nest._kernel_proxy._connect_kernel", side_effect=stub_connect):
            with build_context() as ctx:
                proxy = get_nest_kernel_proxy()
                self.assertIs(proxy, sentinel)
                self.assertIs(proxy, ctx.bsb_nest.kernel)
                # Repeated calls reuse the same proxy (connect only once).
                self.assertIs(get_nest_kernel_proxy(), sentinel)
                self.assertEqual(shutdowns, [])
            self.assertEqual(shutdowns, [True])


class TestDelayRequiredChecker(unittest.TestCase):
    """Exercises the checker with an in-process ``_Kernel`` standing in for the
    subprocess, to keep these unit tests cheap while running the same code paths.
    """

    @classmethod
    def setUpClass(cls):
        _requires_nest()

    @staticmethod
    def _stub_connect():
        from bsb_nest._kernel_server import _Kernel

        return _Kernel(), lambda: None

    def _patch_kernel(self):
        return patch(
            "bsb_nest._kernel_proxy._connect_kernel", side_effect=self._stub_connect
        )

    def test_static_synapse_requires_delay(self):
        from bsb_nest.connection import NestSynapseSettings

        with (
            self._patch_kernel(),
            build_context(),
            self.assertRaises(RequirementError),
        ):
            NestSynapseSettings({"model": "static_synapse", "weight": 1.0})

    def test_gap_junction_does_not_require_delay(self):
        # gap_junction is a real NEST synapse model with has_delay=False.
        from bsb_nest.connection import NestSynapseSettings

        with self._patch_kernel(), build_context():
            NestSynapseSettings({"model": "gap_junction", "weight": 1.0})

    def test_unknown_synapse_is_hard_error_when_proxy_reachable(self):
        # When the proxy IS reachable, an unknown model name is a real config
        # error; the soft warn-and-fall-back is only for unreachable kernels.
        from bsb_nest.connection import NestSynapseSettings

        with (
            self._patch_kernel(),
            build_context(),
            self.assertRaises(ConfigurationError),
        ):
            NestSynapseSettings(
                {"model": "definitely_not_a_real_model", "weight": 1.0, "delay": 0.5}
            )

    def test_no_context_warns_and_falls_back(self):
        from bsb_nest.connection import _is_delay_required
        from bsb_nest.exceptions import KernelWarning

        with warnings.catch_warnings(record=True) as log:
            warnings.simplefilter("always", KernelWarning)
            # Calling outside a build context: no proxy available.
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

        with (
            patch("bsb_nest._kernel_proxy._connect_kernel", side_effect=boom),
            build_context(),
            warnings.catch_warnings(record=True) as log,
        ):
            warnings.simplefilter("always", KernelWarning)
            result = _is_delay_required({"model": "static_synapse"})
        self.assertFalse(result)
        self.assertTrue(
            any(issubclass(w.category, KernelWarning) for w in log),
            f"Expected a KernelWarning, got: {[w.message for w in log]}",
        )


class TestRealKernelSubprocess(unittest.TestCase):
    """End-to-end check of the actual kernel subprocess, with no stubbing."""

    @classmethod
    def setUpClass(cls):
        _requires_nest()

    def test_subprocess_kernel_answers_queries(self):
        with build_context():
            proxy = get_nest_kernel_proxy()
            self.assertIsNotNone(proxy)
            self.assertIn("static_synapse", proxy.models(mtype="synapses"))
            self.assertTrue(proxy.has_delay("static_synapse"))
            self.assertFalse(proxy.has_delay("gap_junction"))


class TestSimulationModuleLoading(unittest.TestCase):
    """``load_simulation_modules`` finds the enclosing simulation's modules and
    guards against them not being built yet."""

    @staticmethod
    def _sim_and_model():
        from bsb import config

        @config.node
        class Sim:
            modules = config.list(type=str)

        @config.node
        class Model:
            pass

        sim = Sim(modules=["mymod"])
        return sim, Model({}, _parent=sim)

    def test_loads_enclosing_simulation_modules(self):
        from bsb_nest._kernel_proxy import load_simulation_modules

        _, model = self._sim_and_model()

        class FakeProxy:
            loaded = None

            def load_modules(self, modules):
                self.loaded = list(modules)
                return []

        proxy = FakeProxy()
        load_simulation_modules(model, proxy)
        self.assertEqual(proxy.loaded, ["mymod"])

    def test_guards_against_unbuilt_modules(self):
        from bsb_nest._kernel_proxy import load_simulation_modules

        sim, model = self._sim_and_model()
        # Simulate a future attribute reorder where `modules` is not built yet.
        del sim.__dict__["_modules"]

        class FakeProxy:
            def load_modules(self, modules):  # pragma: no cover
                raise AssertionError("must not load against unbuilt modules")

        with self.assertRaises(ConfigurationError):
            load_simulation_modules(model, FakeProxy())
