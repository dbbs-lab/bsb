import unittest

from bsb import config

from bsb_json import get_schema


def test_empty_schema():
    class X:
        pass

    schema = get_schema(X)
    assert schema["type"] == "object"
    assert schema["properties"] == {}
    assert schema["title"] == "Configuration"
    assert schema["$defs"] == {}


def test_schema_attrs():
    class X:
        y = config.attr()

    schema = get_schema(X)
    print(schema)
