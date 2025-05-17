# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

# -- Project information -----------------------------------------------------

project = "Arborize"
copyright = "2020, Robin De Schepper"
author = "Robin De Schepper"

init_file = os.path.join(
    os.path.dirname(__file__), "..", "..", "arborize", "__init__.py"
)
with open(init_file, "r") as f:
    for line in f:
        if "__version__ = " in line:
            exec(line.strip())
            break

# The short X.Y version
version = ".".join(__version__.split(".")[0:2])
# The full version, including alpha/beta/rc tags
release = __version__

autodoc_mock_imports = [
    "glia",
    "patch",
    "mpi4py",
    "mpi4py.MPI",
    "rtree",
    "rtree.index",
    "h5py",
    "joblib",
    "numpy",
    "sklearn",
    "scipy",
    "six",
    "plotly",
    "morphio",
]

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
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

html_theme = "furo"
html_static_path = ["_static"]
