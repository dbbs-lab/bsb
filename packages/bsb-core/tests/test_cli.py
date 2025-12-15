import importlib.metadata
import os
import sys
import unittest

from bsb_test import (
    FixedPosConfigFixture,
    NumpyTestCase,
    RandomStorageFixture,
    skip_parallel,
)

from bsb import Scaffold


class TestCLI(unittest.TestCase):
    @skip_parallel
    def test_availability(self):
        import subprocess

        # Ensure that the current interpreter can be detected from the subprocess via PATH
        os.environ["PATH"] += ":" + os.path.join(sys.prefix, "bin")

        our_version = bytes(
            f"bsb {importlib.metadata.version('bsb-core')}", encoding="utf-8"
        )
        # Split on newlines to ignore any prepended spammy output in case of environment
        # specific warnings when running BSB commands.
        cli_version = subprocess.check_output(["bsb", "--version"]).split(b"\n")[-2]
        # Remove \r on Windows
        cli_version = cli_version.replace(b"\r", b"")
        self.assertEqual(our_version, cli_version, "Could not access the BSB through CLI")

    def test_defaults(self):
        import bsb.options

        # Test the default verbosity
        self.assertEqual(1, bsb.options.verbosity)
        # Test disabled because there's currently no options without script descr.
        # # Test that an option without script descriptor isn't registered
        # self.assertRaises(bsb.exceptions.OptionError, lambda: bsb.options.config)

    def test_env_descriptor(self):
        import os

        import bsb.options
        from bsb import BsbOption

        class TestOption(BsbOption, name="_test_", env=("GRZLGRK",), script=("GRZLGRK",)):
            pass

        TestOption.register()
        o = TestOption()

        # Assert that we start out clean
        self.assertEqual(o.get(), None)
        # Test env functionality
        os.environ["GRZLGRK"] = "Hello"
        self.assertEqual(o.get(), "Hello")
        # Test env removed functionality
        del os.environ["GRZLGRK"]
        self.assertEqual(o.get(), None)
        # Test env override by script
        bsb.options.GRZLGRK = "Bye"
        os.environ["GRZLGRK"] = "Hello"
        self.assertEqual(o.get(), "Bye")
        del os.environ["GRZLGRK"]
        o.unregister()


class TestOptions(unittest.TestCase):
    def test_get_cli_tags(self):
        from bsb import BsbOption

        class t1(BsbOption, name="t1", cli=("a",)):
            pass

        class t2(BsbOption, name="t2", cli=("a", "b")):
            pass

        class t3(BsbOption, name="t3", cli=("a", "ave")):
            pass

        class t4(BsbOption, name="t4", cli=("cC")):
            pass

        self.assertEqual(["-a"], t1().get_cli_tags())
        self.assertEqual(["-a", "-b"], t2().get_cli_tags())
        self.assertEqual(["-a", "--ave"], t3().get_cli_tags())
        self.assertEqual(["-c", "-C"], t4().get_cli_tags())

    def test_plugins(self):
        # Test that the plugins are loaded and their script options work
        pass

    def test_register(self):
        import bsb.exceptions
        import bsb.options
        from bsb import BsbOption

        # Test that registering an option into the module works
        class t1(BsbOption, name="testTTTT", script=("aaa",)):
            def get_default(self):
                return 5

        opt = t1.register()
        self.assertEqual(5, bsb.options.aaa)
        opt.unregister()
        self.assertRaises(bsb.exceptions.OptionError, lambda: bsb.options.aaa)


@skip_parallel
class TestCLICommands(
    FixedPosConfigFixture,
    RandomStorageFixture,
    NumpyTestCase,
    unittest.TestCase,
    engine_name="hdf5",
):
    def setUp(self):
        super().setUp()
        self.cfg.connectivity.add(
            "all_to_all",
            dict(
                strategy="bsb.connectivity.AllToAll",
                presynaptic=dict(cell_types=["test_cell"]),
                postsynaptic=dict(cell_types=["test_cell"]),
            ),
        )
        self.cfg.simulations.add(
            "test",
            simulator="arbor",
            duration=100,
            resolution=1.0,
            cell_models=dict(),
            connection_models=dict(),
            devices=dict(),
        )
        self.network = Scaffold(self.cfg, self.storage)
        self.network.compile(clear=True)

    def test_simulate(self):
        import subprocess

        # test correct behavior
        result = subprocess.run(["bsb", "simulate", self.storage.root, "test"])
        self.assertEqual(result.returncode, 0)
        nio_files = [
            filename for filename in os.listdir("./") if filename.endswith(".nio")
        ]
        self.assertEqual(len(nio_files), 1)
        for filename in nio_files:
            os.remove(filename)

    def test_errors_simulate(self):
        import subprocess

        # wrong simulation name
        result = subprocess.run(
            ["bsb", "simulate", self.storage.root, "testA"], capture_output=True
        )
        self.assertEqual(result.returncode, 1)
        # output folder not empty
        result = subprocess.run(
            ["bsb", "simulate", self.storage.root, "test", "-o", os.getcwd()],
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertEqual(
            result.stdout.split("\n")[-2],
            f"Could not create '{os.getcwd()}', directory exists. "
            "Use flag '--exists' to ignore this error.",
        )
        # check exists flag
        result = subprocess.run(
            ["bsb", "simulate", self.storage.root, "test", "-o", os.getcwd(), "--exists"]
        )
        self.assertEqual(result.returncode, 0)
        nio_files = [
            filename for filename in os.listdir("./") if filename.endswith(".nio")
        ]
        self.assertEqual(len(nio_files), 1)
        for filename in nio_files:
            os.remove(filename)
