from os.path import dirname, join

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
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

project = "BSB HDF5 Storage Engine"
copyright = "2022, Robin De Schepper"
author = "Robin De Schepper"

# Fetch the `__version__`
project_folder = dirname(dirname(__file__))
bsb_init_file = join(project_folder, "pyproject.toml")
_findver = "version = "
with open(bsb_init_file) as f:
    for line in f:
        if "version = " in line:
            f = line.find(_findver)
            __version__ = eval(line[line.find(_findver) + len(_findver) :])
            break
    else:
        raise Exception(f"No `version` found in '{bsb_init_file}'.")


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
main_folder = join(dirname(dirname(project_folder)), "docs")

extensions = [
    "sphinx.ext.autodoc",
    "sphinxemoji.sphinxemoji",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "numpy": ("https://numpy.org/doc/stable/", None),
    "bsb": ("https://bsb.readthedocs.io/en/latest/", None),
    "errr": ("https://errr.readthedocs.io/en/latest/", None),
    "h5py": ("https://docs.h5py.org/en/latest/", None),
    "mpi4py": ("https://mpi4py.readthedocs.io/en/stable/", None),
}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "alabaster"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]
