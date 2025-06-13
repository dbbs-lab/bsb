from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "Glia Package Manager", Path(__file__).parent.parent, monorepo=True
)

# -- Project information -----------------------------------------------------

project = _project.name
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
    "sphinx.ext.intersphinx",
    *_project.extensions,
]

autodoc_mock_imports = ["patch", "mpi4py"]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "errr": ("https://errr.readthedocs.io/en/latest/", None),
    "arbor": ("https://docs.arbor-sim.org/en/latest/", None),
    **_project.intersphinx,
}

# Add any paths that contain templates here, relative to this directory.
autoclass_content = "both"
autodoc_typehints = "both"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
todo_include_todos = True


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "furo"

html_static_path = [*_project.html_static_path]
html_favicon = _project.html_favicon

html_theme_options = {
    **_project.html_theme_options,
}

html_context = {
    **_project.html_context,
}
