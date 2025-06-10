from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "BSB NEURON extension", Path(__file__).parent.parent, monorepo=True
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

extensions = ["sphinx.ext.autodoc", "sphinx.ext.intersphinx", *_project.extensions]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    **_project.intersphinx,
}

autodoc_mock_imports = ["neuron"]


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
