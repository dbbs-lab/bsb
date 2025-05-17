"""
YAML parser for the BSB framework.
"""

from .components import YamlDependencyNode
from .parser import YAMLConfigurationParser

__version__ = "6.0.0-a2"

__all__ = [
    "YAMLConfigurationParser",
    "YamlDependencyNode",
]
