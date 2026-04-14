from pathlib import Path

import sphinxext.bsb

_project = sphinxext.bsb.Project(
    "BSB OpenTelemetry integration", Path(__file__).parent.parent, monorepo=True
)

project = _project.name
copyright = _project.copyright
author = _project.authors
release = _project.version
version = _project.version

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    *_project.extensions,
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    **_project.intersphinx,
}

autoclass_content = "both"
autodoc_typehints = "both"

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

html_theme = "furo"
html_static_path = [*_project.html_static_path]
html_favicon = _project.html_favicon
html_theme_options = {**_project.html_theme_options}
html_context = {**_project.html_context}