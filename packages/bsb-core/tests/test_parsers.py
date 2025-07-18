import ast
import pathlib
import unittest
from unittest.mock import patch

from bsb.config.parsers import (
    ConfigurationParser,
    ParsesReferences,
    get_configuration_parser,
)
from bsb.exceptions import ConfigurationWarning, FileReferenceError, PluginError


def get_content(file: str):
    return (pathlib.Path(__file__).parent / "data/configs" / file).read_text()


class RefParserMock(ParsesReferences, ConfigurationParser):
    data_description = "txt"
    data_extensions = ("txt",)

    def parse(self, content, path=None):
        if isinstance(content, str):
            content = ast.literal_eval(content)
        return content, {"meta": path}

    def generate(self, tree, pretty=False):
        # Should not be called.
        pass


class RefParserMock2(ParsesReferences, ConfigurationParser):
    data_description = "bla"
    data_extensions = ("bla",)

    def parse(self, content, path=None):
        if isinstance(content, str):
            content = content.replace("<", "{")
            content = content.replace(">", "}")
            content = ast.literal_eval(content)
        return content, {"meta": path}

    def generate(self, tree, pretty=False):
        # Should not be called.
        pass


class TestParsersBasics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = RefParserMock()

    def test_get_parser(self):
        self.assertRaises(PluginError, get_configuration_parser, "doesntexist")

    def test_parse_empty_doc(self):
        tree, meta = self.parser.parse({})
        self.assertEqual({}, tree, "'{}' parse should produce empty dict")

    def assert_basics(self, tree, meta):
        self.assertEqual(3, tree["list"][2], "Incorrectly parsed basic Txt")
        self.assertEqual(
            "just like that",
            tree["nest me hard"]["oh yea"],
            "Incorrectly parsed nested File",
        )
        self.assertEqual(
            "<parsed file config '[1, 2, 3, 'waddup']' at '/list'>", str(tree["list"])
        )

    def test_parse_basics(self):
        # test from str
        self.assert_basics(*self.parser.parse(get_content("basics.txt")))

        # test from dict
        content = {
            "hello": "world",
            "list": [1, 2, 3, "waddup"],
            "nest me hard": {"oh yea": "just like that"},
        }
        self.assert_basics(*self.parser.parse(content))


class TestFileRef(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = RefParserMock()

    def test_indoc_reference(self):
        content = ast.literal_eval(get_content("indoc_reference.txt"))
        tree, meta = self.parser.parse(content)
        self.assertNotIn("$ref", tree["refs"]["whats the"], "Ref key not removed")
        self.assertEqual("key", tree["refs"]["whats the"]["secret"])
        self.assertEqual("is hard", tree["refs"]["whats the"]["nested secrets"]["vim"])
        self.assertEqual("convoluted", tree["refs"]["whats the"]["nested secrets"]["and"])
        # Checking str keys order.
        self.assertEqual(
            str(tree["refs"]["whats the"]["nested secrets"]),
            "<parsed file config '{'vim': 'is hard', 'and': 'convoluted'}'"
            + " at '/refs/whats the/nested secrets'>",
        )
        self.assertEqual(tree["refs"]["whats the"], tree["refs"]["omitted_doc"])
        content["get"]["a"] = "secret"
        with self.assertRaises(FileReferenceError, msg="Should raise 'ref not a dict'"):
            tree, meta = self.parser.parse(content)

    @patch("bsb.config.parsers.get_configuration_parser_classes")
    def test_far_references(self, get_content_mock):
        # Override get_configuration_parser to manually register RefParserMock
        get_content_mock.return_value = {"txt": RefParserMock, "bla": RefParserMock2}
        content = {
            "refs": {
                "whats the": {"$ref": "basics.txt#/nest me hard"},
                "and": {"$ref": "indoc_reference.txt#/refs/whats the"},
                "far": {"$ref": "far/targetme.bla#/this/key"},
            },
            "target": {"for": "another"},
        }
        tree, meta = self.parser.parse(
            content,
            path=str(
                pathlib.Path(__file__).parent / "data" / "configs" / "interdoc_refs.txt"
            ),
        )
        self.assertIn("was", tree["refs"]["far"])
        self.assertEqual("in another folder", tree["refs"]["far"]["was"])
        self.assertIn("oh yea", tree["refs"]["whats the"])
        self.assertEqual("just like that", tree["refs"]["whats the"]["oh yea"])

    @patch("bsb.config.parsers.get_configuration_parser_classes")
    def test_double_ref(self, get_content_mock):
        # Override get_configuration_parser to manually register RefParserMock
        get_content_mock.return_value = {"txt": RefParserMock, "bla": RefParserMock2}
        tree, meta = self.parser.parse(
            get_content("doubleref.txt"),
            path=str(
                pathlib.Path(__file__).parent / "data" / "configs" / "doubleref.txt"
            ),
        )
        # Only the latest ref is included because the literal_eval keeps only the latest
        # value for similar keys
        self.assertNotIn("oh yea", tree["refs"]["whats the"])
        self.assertIn("for", tree["refs"]["whats the"])
        self.assertIn("another", tree["refs"]["whats the"]["for"])

    @patch("bsb.config.parsers.get_configuration_parser_classes")
    def test_ref_str(self, get_content_mock):
        # Override get_configuration_parser to manually register RefParserMock
        get_content_mock.return_value = {"txt": RefParserMock, "bla": RefParserMock2}
        tree, meta = self.parser.parse(
            get_content("doubleref.txt"),
            path=str(
                pathlib.Path(__file__).parent / "data" / "configs" / "doubleref.txt"
            ),
        )
        self.assertTrue(str(self.parser.references[0]).startswith("<file ref '"))
        # Convert windows backslashes
        wstr = str(self.parser.references[0]).replace("\\", "/")
        self.assertTrue(
            wstr.endswith("/bsb-core/tests/data/configs/indoc_reference.txt#/target'>")
        )

    @patch("bsb.config.parsers.get_configuration_parser_classes")
    def test_wrong_ref(self, get_content_mock):
        # Override get_configuration_parser to manually register RefParserMock
        get_content_mock.return_value = {"txt": RefParserMock, "bla": RefParserMock2}

        content = {"refs": {"whats the": {"$ref": "basics.txt#/oooooooooooooo"}}}
        with self.assertRaises(FileReferenceError, msg="ref should not exist"):
            self.parser.parse(
                content,
                path=str(
                    pathlib.Path(__file__).parent / "data" / "configs" / "wrong_ref.txt"
                ),
            )


class TestFileImport(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parser = RefParserMock()

    def test_indoc_import(self):
        tree, meta = self.parser.parse(get_content("indoc_import.txt"))
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("are", tree["imp"]["importable"]["dicts"]["that"])

    def test_indoc_import_list(self):
        from bsb.config._parse_types import parsed_list

        content = ast.literal_eval(get_content("indoc_import.txt"))
        content["arr"]["with"] = ["a", "b", ["a", "c"]]
        tree, meta = self.parser.parse(content)
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("a", tree["imp"]["with"][0])
        self.assertEqual(parsed_list, type(tree["imp"]["with"][2]), "message")

    def test_indoc_import_value(self):
        content = ast.literal_eval(get_content("indoc_import.txt"))
        content["arr"]["with"] = "a"
        tree, meta = self.parser.parse(content)
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("a", tree["imp"]["with"])

    def test_import_merge(self):
        tree, meta = self.parser.parse(get_content("indoc_import_merge.txt"))
        self.assertEqual(2, len(tree["imp"].keys()))
        self.assertIn("importable", tree["imp"])
        self.assertIn("with", tree["imp"])
        self.assertEqual(
            ["importable", "with"],
            list(tree["imp"].keys()),
            "Imported keys should follow on original keys",
        )
        self.assertEqual(4, tree["imp"]["importable"]["dicts"]["that"])
        self.assertEqual("eh", tree["imp"]["importable"]["dicts"]["even"]["nested"])
        self.assertEqual(["new", "list"], tree["imp"]["importable"]["dicts"]["with"])

    def test_import_overwrite(self):
        content = ast.literal_eval(get_content("indoc_import.txt"))
        content["imp"]["importable"] = 10

        with self.assertWarns(ConfigurationWarning) as _warning:
            tree, meta = self.parser.parse(content)
        self.assertEqual(2, len(tree["imp"].keys()))
        self.assertIn("importable", tree["imp"])
        self.assertIn("with", tree["imp"])
        self.assertEqual(
            ["importable", "with"],
            list(tree["imp"].keys()),
            "Imported keys should follow on original keys",
        )
        self.assertEqual(10, tree["imp"]["importable"])

    @patch("bsb.config.parsers.get_configuration_parser_classes")
    def test_outdoc_import_merge(self, get_content_mock):
        # Override get_configuration_parser to manually register RefParserMock
        get_content_mock.return_value = {"txt": RefParserMock, "bla": RefParserMock2}

        file = "outdoc_import_merge.txt"
        tree, meta = self.parser.parse(
            get_content(file),
            path=pathlib.Path(__file__).parent / "data/configs" / file,
        )

        expected = {
            "with": {},
            "importable": {
                "dicts": {
                    "that": "are",
                    "even": {"nested": "eh"},
                    "with": ["new", "list"],
                    "vim": "is hard",
                },
                "diff": "added",
            },
        }
        self.assertTrue(expected == tree["imp"])
