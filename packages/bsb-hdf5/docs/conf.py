from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "BSB HDF5 extension", Path(__file__).parent.parent, monorepo=True
)


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = _project.name
copyright = _project.copyright
author = _project.authors
release = _project.version
version = _project.version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinxemoji.sphinxemoji",
    "sphinx.ext.intersphinx",
    "sphinx_design",
    *_project.extensions,
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "errr": ("https://errr.readthedocs.io/en/latest/", None),
    "h5py": ("https://docs.h5py.org/en/latest/", None),
    "mpi4py": ("https://mpi4py.readthedocs.io/en/stable/", None),
    **_project.intersphinx,
}

autoclass_content = "both"
autodoc_typehints = "both"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

html_static_path = [*_project.html_static_path]
html_favicon = _project.html_favicon

html_theme_options = {
    **_project.html_theme_options,
}

html_context = {
    **_project.html_context,
}
