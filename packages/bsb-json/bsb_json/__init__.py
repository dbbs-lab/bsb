"""
JSON parser and utilities for the BSB.
"""

from .parser import JsonParser
from .schema import get_json_schema, get_schema

__version__ = "6.0.0-a2"

__all__ = [
    "get_json_schema",
    "get_schema",
    "JsonParser",
]
