from pathlib import Path

import sphinxext.bsb

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Use sphinxext.bsb to help configure this monorepo package
_project = sphinxext.bsb.Project(
    "Arborize model builder", Path(__file__).parent.parent, monorepo=True
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

autodoc_mock_imports = ["glia", "patch", "mpi4py", "neuron"]

autodoc_type_aliases = {
    "NDArray": "numpy.ndarray",
    "np.float64": "float",
    "np.float_": "float",
    "numpy.float64": "float",
    "SynapseConstraintsDict": "arborize.constraints.SynapseConstraintsDict",
}

# Somehow these won't resolve
nitpick_ignore = [
    ("py:class", "numpy.float64"),
    ("py:class", "numpy.float_"),
]


intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "numpy": ("https://numpy.org/doc/stable/", None),
    "scipy": ("https://scipy.github.io/devdocs/", None),
    "errr": ("https://errr.readthedocs.io/en/latest/", None),
    "mpi4py": ("https://mpi4py.readthedocs.io/en/stable/", None),
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

html_static_path = ["_static", *_project.html_static_path]
html_favicon = _project.html_favicon

html_theme_options = {
}

html_context = {
    **_project.html_context,
}
