from os.path import dirname, join

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# Fetch the `__version__`
bsb_folder = dirname(dirname(__file__))
bsb_init_file = join(bsb_folder, "pyproject.toml")
_findver = "version = "
with open(bsb_init_file) as f:
    for line in f:
        if "version = " in line:
            f = line.find(_findver)
            __version__ = eval(line[line.find(_findver) + len(_findver) :])
            break
    else:
        raise Exception(f"No `version` found in '{bsb_init_file}'.")

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Brain Scaffold Builder'
copyright = '2025, DBBS University of Pavia'
author = 'Robin De Schepper'

release = __version__

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
    "bsbdocs",
    "sphinxcontrib.collections"
]
autodoc_typehints = "both"
autoclass_content = "both"

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

collections = {
    "bsb-core": {
        "driver": "copy_folder",
        "source": join(bsb_folder, "packages", "bsb-core", "docs/"),
        "target": "bsb-core/",
        "ignore": ["index.rst", "genindex.rst", "py-modindex.rst"]
    },
    "bsb-hdf5": {
        "driver": "copy_folder",
        "source": join(bsb_folder, "packages", "bsb-hdf5", "docs/"),
        "target": "bsb-hdf5/",
        "ignore": ["index.rst", "genindex.rst", "py-modindex.rst"]
    },
}

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
todo_include_todos = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'

html_static_path = [join(bsb_folder, "docs", '_static')]

html_theme_options = {
    "light_logo": "bsb.svg",
    "dark_logo": "bsb_dark.svg",
    "sidebar_hide_name": True,
}

html_favicon = join(html_static_path[0], "bsb_ico.svg")