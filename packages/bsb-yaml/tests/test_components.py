import pathlib
import unittest

from bsb import CastError, config

from bsb_yaml.components import YamlDependencyNode


class TestYamlNode(unittest.TestCase):
    def test_yaml(self):
        @config.node
        class Test:
            c = config.attr(type=YamlDependencyNode)

        b = Test(c=pathlib.Path(__file__).parent / "test_yaml.yaml")
        tested = b.c.load_object()
        expected = dict(testKey={"testSubKey": ["content1", 2, 3.0], 4: None})
        self.assertEqual(expected, tested, "Yaml parsing failed")
        self.assertRaises(CastError, Test, c=2)
        d = Test(c="test.yaml")
        self.assertRaises(FileNotFoundError, d.c.load_object)
