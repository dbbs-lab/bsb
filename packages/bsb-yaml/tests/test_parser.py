import unittest

from bsb import get_configuration_parser


class TestYAML(unittest.TestCase):
    def test_yaml_parse(self):
        yaml = get_configuration_parser("yaml")
        tree, meta = yaml.parse("some_key: 5")
        self.assertEqual({"some_key": 5}, tree)

    def test_yaml_generate(self):
        yaml = get_configuration_parser("yaml")
        content = yaml.generate({"some_key": 5})
        self.assertEqual("some_key: 5\n", content)
