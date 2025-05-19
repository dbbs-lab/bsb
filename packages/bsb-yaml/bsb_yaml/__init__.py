"""
YAML parser for the BSB framework.
"""

from .components import YamlDependencyNode
from .parser import YAMLConfigurationParser

__all__ = [
    "YAMLConfigurationParser",
    "YamlDependencyNode",
]
