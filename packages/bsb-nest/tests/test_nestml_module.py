import tempfile
import unittest
from os.path import dirname, join

from bsb import config
from bsb.config import build_context

from bsb_nest import get_nest_kernel_proxy

# Name of the module produced from tests/data/nestml and the node model it provides.
_MODULE = "bsbtestmodule"
_MODEL = "bsb_test_neuron"


def _build_test_module():
    """Build the minimal NESTML test module, installing it into NEST.

    Returns ``None`` on success or a skip reason. NESTML and a C++ toolchain
    are an optional, version-coupled toolchain, so any failure to build skips
    rather than fails the suite.
    """
    try:
        import nest  # noqa: F401
    except ImportError as e:
        return f"NEST is not installed: {e}"
    try:
        from pynestml.frontend.pynestml_frontend import generate_target
    except ImportError as e:
        return f"NESTML (pynestml) is not installed: {e}"
    try:
        generate_target(
            input_path=join(dirname(__file__), "data", "nestml"),
            target_platform="NEST",
            target_path=tempfile.mkdtemp(prefix="bsb-nestml-"),
            module_name=_MODULE,
        )
    except Exception as e:
        return f"Could not build the NESTML test module: {e}"
    return None


class TestNestmlExtensionModule(unittest.TestCase):
    """bsb-nest can load and validate against a built NESTML extension module.

    Exercises the out-of-process kernel proxy with a real, freshly built module:
    the build process imports ``nest`` (to compile the module), and the kernel
    subprocess then installs that module independently.
    """

    @classmethod
    def setUpClass(cls):
        reason = _build_test_module()
        if reason:
            raise unittest.SkipTest(reason)

    def test_module_loads_into_build_proxy(self):
        with build_context():
            proxy = get_nest_kernel_proxy()
            self.assertEqual(proxy.load_modules([_MODULE]), [])
            self.assertIn(_MODEL, proxy.models(mtype="nodes"))

    def test_module_does_not_leak_into_main_process(self):
        import nest

        # The build compiled and installed the module to disk but did not load
        # it into this (main) process's kernel.
        self.assertNotIn(_MODEL, nest.node_models)
        with build_context():
            proxy = get_nest_kernel_proxy()
            proxy.load_modules([_MODULE])
            # Available in the out-of-process kernel...
            self.assertIn(_MODEL, proxy.models(mtype="nodes"))
        # ...but the in-process kernel is never touched: the whole point of the
        # proxy is that building a config does not mutate the main process.
        self.assertNotIn(_MODEL, nest.node_models)

    def test_module_provided_cell_model_validates(self):
        from bsb_nest.cell import nest_node_model

        @config.node
        class Sim:
            modules = config.list(type=str)

        @config.node
        class Holder:
            model = config.attr(type=nest_node_model())

        with build_context():
            sim = Sim(modules=[_MODULE])
            holder = Holder({"model": _MODEL}, _parent=sim)
            self.assertEqual(holder.model, _MODEL)

    def test_unknown_model_from_module_is_rejected(self):
        from bsb_nest.cell import nest_node_model

        @config.node
        class Sim:
            modules = config.list(type=str)

        @config.node
        class Holder:
            model = config.attr(type=nest_node_model())

        from bsb import ConfigurationError

        with build_context(), self.assertRaises(ConfigurationError):
            sim = Sim(modules=[_MODULE])
            Holder({"model": "not_a_real_model"}, _parent=sim)
