import importlib.metadata
import os
from pathlib import Path

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information


project = "Brain Scaffold Builder"
copyright = "2022, DBBS University of Pavia"
author = "Robin De Schepper"
project_folder = Path(__file__).parent.parent
package_name = project_folder.stem

# Fetch the version
version = importlib.metadata.version(package_name)
# Determine whether we build from local sources
BSB_LOCAL_INTERSPHINX_ONLY = os.getenv("BSB_LOCAL_INTERSPHINX_ONLY", "false") == "true"
# The full version, including alpha/beta/rc tags
release = version

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

autodoc_typehints = "both"


extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxemoji.sphinxemoji",
    "sphinx_design",
    "sphinx_copybutton",
    "sphinxext.bsb",
]

autodoc_mock_imports = [
    "glia",
    "patch",
    "mpi4py",
    "rtree",
    "rtree.index",
    "mpi4py.MPI",
    "dbbs_models",
    "arborize",
    "h5py",
    "joblib",
    "sklearn",
    "scipy",
    "six",
    "plotly",
    "psutil",
    "mpilock",
    "zwembad",
    "arbor",
    "morphio",
    "nrrd",
]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "packaging": ("https://packaging.pypa.io/en/stable/", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://scipy.github.io/devdocs/", None),
    "errr": ("https://errr.readthedocs.io/en/latest/", None),
    "mpi4py": ("https://mpi4py.readthedocs.io/en/stable/", None),
    "arbor": ("https://docs.arbor-sim.org/en/latest/", None),
    "neo": ("https://neo.readthedocs.io/en/latest/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = [
    "_build",
    "Thumbs.db",
    ".DS_Store",
]

autoclass_content = "both"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"

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
    "project_pretty_name": "BSB",
    "projects": {"DBBS Scaffold": "https://github.com/dbbs/bsb"},
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".

todo_include_todos = True
suppress_warnings = ["ref.ref"]
