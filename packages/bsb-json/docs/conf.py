from os.path import dirname, join

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

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

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'BSB JSON Configuration File Parser'
copyright = '2025, DBBS University of Pavia'
author = 'Robin De Schepper'

# The full version, including alpha/beta/rc tags
release = __version__

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

main_folder = dirname(dirname(project_folder))

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "bsb": (join(main_folder, "packages", "bsb-core", "docs", "_build", "html"), None),
}

autoclass_content = "both"
autodoc_typehints = "both"

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'

html_static_path = [join(main_folder, "docs", '_static')]

html_theme_options = {
    "light_logo": "bsb.svg",
    "dark_logo": "bsb_dark.svg",
    "sidebar_hide_name": True,
}

html_favicon = join(html_static_path[0], "bsb_ico.svg")

html_context = {
    "maintainer": "Robin De Schepper",
    "project_pretty_name": "BSB-JSON",
    "projects": {"DBBS Scaffold": "https://github.com/dbbs/bsb"},
}
