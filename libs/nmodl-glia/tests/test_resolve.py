import unittest

from glia.assets import Mod, Package
from glia.resolution import Resolver


class ManagerMock:
    def __init__(self, packages):
        self.packages = packages


class TestResolver(unittest.TestCase):
    """
    Check if packages can be discovered.
    """

    def test_resolve(self):
        pkg = Package(
            "test", __file__, mods=[m := Mod("./doesntexist", "hello", variant="test_v")]
        )
        mname = m.mod_name
        pkg.mods = [m]
        resolver = Resolver(ManagerMock([pkg]))
        self.assertEqual(mname, resolver.resolve("hello"))
        self.assertEqual(mname, resolver.resolve("hello", pkg="test", variant="test_v"))
        # Test the tuple forms
        self.assertEqual(mname, resolver.resolve(("hello",)))
        self.assertEqual(mname, resolver.resolve(("hello", "test_v", "test")))
