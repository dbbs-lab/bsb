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


class _FakeKernel:
    """In-process stand-in for the NEST kernel that tracks installed modules.

    Modules contribute extra model names that exist only while the module is
    loaded, like a NEST dynamic module. The kernel keeps every module it
    installs for its lifetime, so each ``_FakeKernel`` instance represents a
    single subprocess that cannot unload a module once installed.
    """

    MODULE_MODELS = {"sim1mod": ["mod1_model"], "sim2mod": ["mod2_model"]}
    BASE_MODELS = ["static_synapse"]

    instances = []

    def __init__(self):
        self._loaded = set()
        type(self).instances.append(self)

    def load_modules(self, modules):
        missing = []
        for module in modules:
            if module in self._loaded:
                continue
            if module not in self.MODULE_MODELS:
                missing.append(module)
                continue
            self._loaded.add(module)
        return missing

    def models(self, mtype=None):
        models = list(self.BASE_MODELS)
        for module in self._loaded:
            models.extend(self.MODULE_MODELS[module])
        return models


class TestKernelSimulationIsolation(unittest.TestCase):
    """A module loaded for one simulation must not leak into the validation of a
    later simulation: each simulation is validated against a kernel carrying only
    its own modules, achieved by respawning the kernel at simulation boundaries.
    """

    @staticmethod
    def _two_sims():
        from bsb import config

        @config.node
        class Sim:
            modules = config.list(type=str)

        @config.node
        class Model:
            pass

        sim1 = Sim(modules=["sim1mod"])
        sim2 = Sim(modules=["sim2mod"])
        return (
            Model({}, _parent=sim1),
            Model({}, _parent=sim2),
        )

    def _patch_kernel(self):
        _FakeKernel.instances = []
        return patch(
            "bsb_nest._kernel_proxy._connect_kernel",
            side_effect=lambda: (_FakeKernel(), lambda: None),
        )

    def test_module_does_not_leak_across_simulations(self):
        from bsb_nest._kernel_proxy import (
            get_nest_kernel_proxy,
            load_simulation_modules,
        )

        model1, model2 = self._two_sims()
        with self._patch_kernel(), build_context():
            proxy1 = get_nest_kernel_proxy()
            proxy1 = load_simulation_modules(model1, proxy1) or proxy1
            # Sim 1's module model is available while validating sim 1.
            self.assertIn("mod1_model", proxy1.models())

            proxy2 = get_nest_kernel_proxy()
            proxy2 = load_simulation_modules(model2, proxy2) or proxy2
            # Moving to sim 2 respawns the kernel, so sim 1's module is gone and
            # only sim 2's module is available.
            self.assertNotIn("mod1_model", proxy2.models())
            self.assertIn("mod2_model", proxy2.models())

        # A fresh subprocess was spawned for the second simulation.
        self.assertEqual(len(_FakeKernel.instances), 2)

    def test_same_simulation_reuses_kernel(self):
        from bsb_nest._kernel_proxy import (
            get_nest_kernel_proxy,
            load_simulation_modules,
        )

        model1, _ = self._two_sims()
        with self._patch_kernel(), build_context():
            proxy = get_nest_kernel_proxy()
            load_simulation_modules(model1, proxy)
            load_simulation_modules(model1, proxy)

        # Repeated validation within one simulation does not respawn the kernel.
        self.assertEqual(len(_FakeKernel.instances), 1)
