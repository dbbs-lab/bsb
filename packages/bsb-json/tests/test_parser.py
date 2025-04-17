import pathlib
import unittest

from bsb import ConfigurationWarning, PluginError, get_configuration_parser
from bsb.exceptions import FileReferenceError


def get_content(file: str):
    return (pathlib.Path(__file__).parent / "parser_tests" / file).read_text()


class TestJsonBasics(unittest.TestCase):
    def test_get_parser(self):
        get_configuration_parser("json")
        self.assertRaises(PluginError, get_configuration_parser, "doesntexist")

    def test_parse_empty_doc(self):
        tree, meta = get_configuration_parser("json").parse(get_content("doc.json"))
        self.assertEqual({}, tree, "'doc.json' parse should produce empty dict")

    def test_parse_basics(self):
        tree, meta = get_configuration_parser("json").parse(get_content("basics.json"))
        self.assertEqual(3, tree["list"][2], "Incorrectly parsed basic JSON")
        self.assertEqual(
            "just like that",
            tree["nest me hard"]["oh yea"],
            "Incorrectly parsed nested JSON",
        )
        self.assertEqual(
            "<parsed file config '[1, 2, 3, 'waddup']' at '/list'>", str(tree["list"])
        )


class TestJsonRef(unittest.TestCase):
    def test_indoc_reference(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("intradoc_refs.json")
        )
        self.assertNotIn("$ref", tree["refs"]["whats the"], "Ref key not removed")
        self.assertEqual("key", tree["refs"]["whats the"]["secret"])
        self.assertEqual("is hard", tree["refs"]["whats the"]["nested secrets"]["vim"])
        self.assertEqual(
            "convoluted", tree["refs"]["whats the"]["nested secrets"]["and"]
        )
        self.assertEqual(tree["refs"]["whats the"], tree["refs"]["omitted_doc"])
        with self.assertRaises(FileReferenceError, msg="Should raise 'ref not a dict'"):
            tree, meta = get_configuration_parser("json").parse(
                get_content("intradoc_nodict_ref.json")
            )

    def test_far_references(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("interdoc_refs.json"),
            path=str(
                (pathlib.Path(__file__).parent / "parser_tests" / "interdoc_refs.json")
            ),
        )
        self.assertIn("was", tree["refs"]["far"])
        self.assertEqual("in another folder", tree["refs"]["far"]["was"])
        self.assertIn("oh yea", tree["refs"]["whats the"])
        self.assertEqual("just like that", tree["refs"]["whats the"]["oh yea"])

    def test_double_ref(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("doubleref.json"),
            path=str(
                (pathlib.Path(__file__).parent / "parser_tests" / "doubleref.json")
            ),
        )

    def test_ref_str(self):
        parser = get_configuration_parser("json")
        tree, meta = parser.parse(
            get_content("doubleref.json"),
            path=str(
                (pathlib.Path(__file__).parent / "parser_tests" / "doubleref.json")
            ),
        )
        self.assertTrue(str(parser.references[0]).startswith("<file ref '"))
        # Convert windows backslashes
        wstr = str(parser.references[0]).replace("\\", "/")
        self.assertTrue(
            wstr.endswith("/bsb-json/tests/parser_tests/interdoc_refs.json#/target'>")
        )


class TestJsonImport(unittest.TestCase):
    def test_indoc_import(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("indoc_import.json")
        )
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("are", tree["imp"]["importable"]["dicts"]["that"])

    def test_indoc_import_list(self):
        from bsb.config._parse_types import parsed_list

        tree, meta = get_configuration_parser("json").parse(
            get_content("indoc_import_list.json")
        )
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("a", tree["imp"]["with"][0])
        self.assertEqual(parsed_list, type(tree["imp"]["with"][2]), "message")

    def test_indoc_import_value(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("indoc_import_other.json")
        )
        self.assertEqual(["with", "importable"], list(tree["imp"].keys()))
        self.assertEqual("a", tree["imp"]["with"])

    def test_import_merge(self):
        tree, meta = get_configuration_parser("json").parse(
            get_content("indoc_import_merge.json")
        )
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
        with self.assertWarns(ConfigurationWarning) as warning:
            tree, meta = get_configuration_parser("json").parse(
                get_content("indoc_import_overwrite.json")
            )
        self.assertEqual(2, len(tree["imp"].keys()))
        self.assertIn("importable", tree["imp"])
        self.assertIn("with", tree["imp"])
        self.assertEqual(
            ["importable", "with"],
            list(tree["imp"].keys()),
            "Imported keys should follow on original keys",
        )
        self.assertEqual(10, tree["imp"]["importable"])

    def test_far_import(self):
        pass
