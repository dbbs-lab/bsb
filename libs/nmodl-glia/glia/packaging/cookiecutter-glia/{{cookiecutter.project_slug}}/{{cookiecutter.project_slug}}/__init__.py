"""
{{cookiecutter.project_name}}

{{cookiecutter.project_short_description}}

Glia asset bundle. If the Glia Asset Manager (`nmodl-glia`) is installed, the NMODL assets
in this package will automatically be available in your Glia library for use in the Arbor
and NEURON brain simulation engines.
"""

from pathlib import Path

from glia import Package

__version__ = "{{cookiecutter.version}}"

package = Package(
    "{{cookiecutter.project_slug}}",
    Path(__file__).resolve().parent,
    mods=[],
)
