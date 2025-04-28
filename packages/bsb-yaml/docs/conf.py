import importlib.metadata
import os
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


project = 'BSB YAML Configuration File Parser'
copyright = '2025, DBBS University of Pavia'
author = 'Robin De Schepper'
project_folder = Path(__file__).parent.parent
package_name = project_folder.stem

# Fetch the version
version = importlib.metadata.version(package_name)
# Determine whether we build from local sources
BSB_LOCAL_INTERSPHINX_ONLY = os.getenv("BSB_LOCAL_INTERSPHINX_ONLY", "false") == "true"
# The full version, including alpha/beta/rc tags
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]


def interbsb(dep_package):
    local_folder = project_folder / f"../{dep_package}/docs/_build/iso-html"
    remote = f"https://{dep_package}.readthedocs.io"

    if BSB_LOCAL_INTERSPHINX_ONLY:
        return str(local_folder), None
    else:
        return remote, (None, str(local_folder / "objects.inv"))


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "bsb": interbsb("bsb-core"),
}

autoclass_content = "both"
autodoc_typehints = "both"

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'

bsb_doc_static = project_folder / "../../packages/bsb/docs/_static"
html_static_path = [str(bsb_doc_static)]

html_theme_options = {
    "light_logo": "bsb.svg",
    "dark_logo": "bsb_dark.svg",
    "sidebar_hide_name": True,
}

html_favicon = str(bsb_doc_static / "bsb_ico.svg")

html_context = {
    "maintainer": "Robin De Schepper",
    "project_pretty_name": "BSB-YAML",
    "projects": {"DBBS Scaffold": "https://github.com/dbbs/bsb"},
}