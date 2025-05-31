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
        return {
            "light_logo": "bsb.svg",
            "dark_logo": "bsb_dark.svg",
            "sidebar_hide_name": True,
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
