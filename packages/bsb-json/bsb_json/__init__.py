"""
JSON parser and utilities for the BSB.
"""

from .parser import JsonParser
from .schema import get_json_schema, get_schema

__version__ = "4.2.3"

__all__ = [
    "get_json_schema",
    "get_schema",
    "JsonParser"
]