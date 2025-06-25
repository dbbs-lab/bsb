from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "Arborize model builder", Path(__file__).parent.parent, monorepo=True
)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "Patch"
copyright = _project.copyright
author = _project.authors
release = _project.version
version = _project.version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.imgmath",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx_code_tabs",
    "sphinx.ext.intersphinx",
    *_project.extensions,
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

intersphinx_mapping = {
    "neuron": ("https://nrn.readthedocs.io/en/latest/", None),
    **_project.intersphinx,
}

autodoc_mock_imports = ["neuron"]

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

html_static_path = [*_project.html_static_path]
html_favicon = _project.html_favicon

html_context = {
    **_project.html_context,
}

# Mocks
autodoc_mock_imports = ["mpi4py", "neuron"]
