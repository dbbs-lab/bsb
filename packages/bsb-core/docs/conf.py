from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "BSB Framework core", Path(__file__).parent.parent, monorepo=True
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
    "sphinx.ext.todo",
    "sphinx.ext.coverage",
    "sphinx.ext.ifconfig",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinxemoji.sphinxemoji",
    "sphinx_design",
    "sphinx_copybutton",
    *_project.extensions,
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
    "voxcell",
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
    "voxcell": ("https://voxcell.readthedocs.io/en/stable/", None),
    **_project.intersphinx,
}

autoclass_content = "both"
autodoc_typehints = "both"
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
templates_path = ["_templates"]
todo_include_todos = True


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
