import unittest
from time import sleep

from bsb.plugins import discover
from bsb.simulation import SimulationBackendPlugin

from bsb_test import plugin_context, spoof_plugin, spoof_plugins, timeout


class TestTimeout(unittest.TestCase):
    def test_timeout_regular(self):
        @timeout(1)
        def x():
            return 5

        x()

    def test_timeout_timeout(self):
        @timeout(1)
        def x():
            sleep(5)
            return 5

        with self.assertRaises(TimeoutError):
            x()

    def test_timeout_exception(self):
        @timeout(1)
        def x():
            raise ValueError()

        with self.assertRaises(ValueError):
            x()


class TestPluginTesting(unittest.TestCase):
    def test_spoof_plugins(self):
        spy = None

        @spoof_plugins({"cat": {"thing1": [5, 6, 7], "thing2": [5, 6, 7, "oh"]}, "dog": {"thing3": ["ah"]}})
        def exec_spoof():
            nonlocal spy
            spy = discover("cat").copy()

        exec_spoof()
        self.assertEqual({"thing1": [5, 6, 7], "thing2": [5, 6, 7, "oh"]}, spy)
        self.assertEqual({}, discover("cat"))

    def test_spoof_plugin(self):
        spy = None

        @spoof_plugin("cat", "thing1", [5, 6, 7])
        def exec_spoof():
            nonlocal spy
            spy = discover("cat").copy()

        exec_spoof()
        self.assertEqual({"thing1": [5, 6, 7]}, spy)
        self.assertEqual({}, discover("cat"))

    def test_cached_spoof(self):
        """
        Test that plugin categories that have caches get invalidated and take the spoofed
        plugins into account.
        """
        pre_spoof = [*discover("simulation_backends").keys()]
        with plugin_context({"simulation_backends": {"new": SimulationBackendPlugin([], [])}}):
            self.assertEqual(sorted(["new", *pre_spoof]), sorted(discover("simulation_backends").keys()))
        self.assertEqual(sorted(pre_spoof), sorted(discover("simulation_backends").keys()))
