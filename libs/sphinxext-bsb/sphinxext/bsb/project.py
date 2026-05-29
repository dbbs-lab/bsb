import importlib.metadata
import json
import os
from pathlib import Path


class Project:
    def __init__(self, project_name: str, project_folder: Path, monorepo=False):
        self._project_name = project_name
        self._root_folder = project_folder
        self._local_only = os.getenv("BSB_LOCAL_INTERSPHINX_ONLY", "false") == "true"
        self._monorepo = monorepo

    @property
    def name(self):
        return self._project_name

    @property
    def monorepo(self):
        return self._monorepo

    @property
    def copyright(self):
        return "2021-%Y, DBBS University of Pavia"

    @property
    def authors(self):
        return "Robin De Schepper, Dimitri Rodarie, Filippo Marchetti"

    @property
    def package_name(self):
        return self._root_folder.stem

    @property
    def version(self):
        return importlib.metadata.version(self.package_name)

    @property
    def extensions(self):
        return ["sphinxext.bsb"]

    @property
    def intersphinx(self):
        if self._monorepo:
            return {
                _get_mapped_name(pkg): self.interbsb(pkg)
                for pkg in self._get_monorepo_doc_dependencies()
            }
        return {}

    @property
    def _doc_path(self):
        if self._monorepo:
            return self._root_folder / "../../packages/bsb/docs"
        else:
            return self._root_folder / "docs"

    @property
    def html_static_path(self):
        return [str(self._doc_path / "_static")]

    @property
    def html_favicon(self):
        return str(self._doc_path / "_static/bsb_ico.svg")

    @property
    def html_theme_options(self):
        with open(self.html_favicon) as f:
            favicon = "\n".join(f.readlines()[2:])
        return {
            "light_logo": "bsb.svg",
            "dark_logo": "bsb_dark.svg",
            "sidebar_hide_name": True,
            "footer_icons": [
                {
                    "name": "GitHub",
                    "url": "https://github.com/dbbs-lab/bsb",
                    "html": """
                        <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 16 16">
                            <path fill-rule="evenodd" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0 0 16 8c0-4.42-3.58-8-8-8z"></path>
                        </svg>
                    """,  # noqa: E501
                    "class": "",
                },
                {
                    "name": "Main BSB documentation",
                    "url": "https://bsb.readthedocs.io/en/latest/index.html",
                    "html": f"""
                        {favicon}
                    """,
                    "class": "",
                },
            ],
        }

    @property
    def html_context(self):
        return {
            "maintainer": self.authors,
            "project_pretty_name": self.name,
            "projects": {"bsb": "https://github.com/dbbs/bsb"},
        }

    def interbsb(self, dep_package):
        local_folder = (
            self._root_folder / f"../../packages/{dep_package}/docs/_build/iso-html"
        )
        remote = f"https://{dep_package}.readthedocs.io/en/latest"

        if self._local_only:
            return remote, str(local_folder / "objects.inv")
        else:
            return remote, (None, str(local_folder / "objects.inv"))

    def _get_monorepo_project(self):
        return json.loads((self._root_folder / "project.json").read_text())

    def _get_monorepo_doc_dependencies(self):
        project = self._get_monorepo_project()
        doc_dependencies: list[str] = (
            project.get("targets", {}).get("docs", {}).get("dependsOn", [])
        )
        return [k.split(":")[0] for k in doc_dependencies if k.endswith(":iso-docs")]


def _get_mapped_name(bsb_pkg):
    if bsb_pkg == "bsb-core":
        return "bsb"
    else:
        return bsb_pkg.replace("-", "_")
