import json
import unittest
from tempfile import TemporaryFile

from bsb import (
    Configuration,
    Scaffold,
    config,
    parse_configuration_content,
    parse_configuration_file,
)
from bsb_test import RandomStorageFixture, get_test_config_tree


def as_json(name: str):
    import json

    return json.dumps(get_test_config_tree(name))


class TestConfiguration(
    RandomStorageFixture, unittest.TestCase, setup_cls=True, engine_name="fs"
):
    def test_default_bootstrap(self):
        cfg = config.Configuration.default(storage={"engine": "fs"})
        Scaffold(cfg, self.storage)

    def test_json_minimal_bootstrap(self):
        with TemporaryFile(mode="w+") as f:
            f.write(as_json("minimal"))
            f.seek(0)
            config = parse_configuration_file(f, parser="json")
        Scaffold(config, self.storage)

    def test_json_minimal_content_bootstrap(self):
        config = parse_configuration_content(as_json("minimal"), parser="json")
        Scaffold(config, self.storage)

    def test_json_full_bootstrap(self):
        with TemporaryFile(mode="w+") as f:
            f.write(as_json("full_compile"))
            f.seek(0)
            config = parse_configuration_file(f, parser="json")
        Scaffold(config, self.storage)

    def test_full_bijective(self):
        self.bijective(
            "full_compile", Configuration, get_test_config_tree("full_compile")
        )

    def bijective(self, name, cls, tree):
        # Test that the tree and its config projection are the same in JSON
        with self.subTest(name=name):
            cfg = cls(tree)
            new_tree = cfg.__tree__()
            self.assertEqual(json.dumps(tree, indent=2), json.dumps(new_tree, indent=2))
            return cfg, new_tree
