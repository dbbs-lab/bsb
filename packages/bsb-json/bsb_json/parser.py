"""
JSON parsing module.

Built on top of the Python ``json`` module. Adds JSON imports and
references.
"""

import json

import numpy as np
from bsb.config.parsers import ConfigurationParser, ParsesReferences


def _json_iter(obj):  # pragma: nocover
    if isinstance(obj, dict):
        return obj.items()
    elif isinstance(obj, list):
        return iter(obj)
    else:
        return iter(())


def _to_json(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    else:
        raise TypeError(f"Can't encode '{value}' ({type(value)})")


class JsonParser(ParsesReferences, ConfigurationParser):
    """
    Parser plugin class to parse JSON configuration files.
    """

    data_description = "JSON"
    data_extensions = ("json",)
    data_syntax = "json"

    def parse(self, content, path=None):
        if isinstance(content, str):
            content = json.loads(content)
        return content, {"meta": path}

    def generate(self, tree, pretty=False):
        if pretty:
            return json.dumps(tree, indent=4, default=_to_json)
        else:
            return json.dumps(tree, default=_to_json)


__plugin__ = JsonParser
