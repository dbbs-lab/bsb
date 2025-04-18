"""
YAML parser for the BSB framework.
"""

from .components import YamlDependencyNode
from .parser import YAMLConfigurationParser

__version__ = "4.2.3"

__all__ = [
    "YAMLConfigurationParser",
    "YamlDependencyNode",
]
