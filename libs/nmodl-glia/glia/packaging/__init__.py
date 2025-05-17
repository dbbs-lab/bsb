import os
import typing
from pathlib import Path

import toml
from black import find_project_root

from ..assets import Mod, SupportedDialect
from ..exceptions import PackageError, PackageFileError, PackageProjectError
from ._ast import NmodlWriter, PackageTransformer, get_package_transformer


class PackageManager:
    def __init__(self, path: typing.Union[str, os.PathLike]):
        self._path = Path(path).resolve()
        self._pyproject = self._path / "pyproject.toml"
        if not self._pyproject.exists():
            raise PackageProjectError(
                f"'{self._path}' is not a Glia package root (no pyproject.toml)."
            )
        self._defaults = {"package": {"mod-dir": "mods"}}

    @classmethod
    def for_cwd(cls):
        root, method = find_project_root(tuple())
        return cls(root)

    @property
    def path(self):
        return self._path

    def load_pyproject(self):
        return toml.load(self._pyproject)

    def get_entry_point(self) -> str:
        entry_points = [
            *self.load_pyproject()
            .get("project", {})
            .get("entry-points", {})
            .get("glia.package", {})
            .values()
        ]
        if len(entry_points) != 1:
            raise PackageProjectError(
                "Each Glia project must advertise exactly one Glia package."
                ' Please add/modify the [project.entry-points."glia.package"] table in'
                f" '{self._pyproject}' ."
            )
        return entry_points[0]

    def get_module_path(self) -> Path:
        entry_point = self.get_entry_point()
        module_name, attr = _unpack_ep(entry_point)
        found_path = _try_find_project_module(self._path, module_name)
        if found_path is None:
            raise PackageFileError(
                f"Could not find Python file of advertised package '{entry_point}'."
            )
        if found_path.parent == self._path:
            raise PackageProjectError(
                f"Glia package '{found_path}' is directly inside project root."
                " Single file packages cannot bundle NMODL files."
            )
        return found_path

    def _get_transformer(self) -> PackageTransformer:
        entry_point = self.get_entry_point()
        module_name, attr = _unpack_ep(entry_point)
        path = self.get_module_path()
        attr = attr or "package"
        try:
            return get_package_transformer(path, attr)
        except PackageError as e:
            raise PackageError(
                "Could not determine find package declaration "
                f"from entry point '{entry_point}' in '{path}'."
            ) from e

    def get_mod_dir(self, mod_dir: typing.Union[str, Path] = None):
        if mod_dir is None:
            mod_dir = self.get_setting("package", "mod-dir")
        mod_dir = Path(mod_dir)
        return self.get_package_path() / mod_dir

    def get_rel_path(self, mod_dir: typing.Union[str, Path] = None):
        return self.get_mod_dir(mod_dir).relative_to(self.get_package_path())

    def get_package_path(self):
        return self.path / self.get_module_path().relative_to(self.path).parts[0]

    def get_mod_files(self, mod_dir: typing.Union[str, Path] = None):
        return [*(self.get_mod_dir(mod_dir)).rglob("*.mod")]

    def get_mod_declarations(self):
        return self._get_transformer().get_modlist_declaration()

    def add_mod_file(self, source: Path, mod: "Mod"):
        transformer = self._get_transformer()
        mods = transformer.get_mods()
        if any(
            m.asset_name == mod.asset_name
            and m.variant == mod.variant
            and m.dialect == mod.dialect
            for m in mods
        ):
            raise ValueError("A mod with the same spec already exists")
        else:
            dest = self.get_package_path()
            writer = NmodlWriter(mod)
            writer.import_source(source, dest, dialect=mod.dialect)
            transformer.add_mod(mod)
            transformer.write_in_place()

    def get_setting(self, *settings: str):
        node = self.load_pyproject()
        for part in ("tool", "glia", *settings):
            node = node.get(part, None)
            if node is None:
                return self.get_default(*settings)
        return node

    def get_default(self, *settings: str):
        node = self._defaults
        for part in settings:
            node = node.get(part, None)
            if node is None:
                return None
        return node

    def get_package_shim(self):
        return self._get_transformer().get_package_shim()

    def get_mod_from_source(
        self,
        source: Path,
        name: str,
        variant: str = "0",
        dialect: SupportedDialect = None,
    ):
        mod = Mod(
            str(self.get_rel_path() / f"{name}__{variant}.mod"), name, variant=variant
        )
        mod.set_package(self.get_package_shim())
        writer = NmodlWriter(mod)
        writer.parse_source(source, dialect=dialect)
        writer.extract_source_info()
        return mod


def _try_find_project_module(path: Path, module_name) -> Path:
    module_root = path / module_name.replace(".", os.sep)
    module_path = module_root.with_suffix(".py")
    if module_path.exists():
        return module_path
    package_path = module_root / "__init__.py"
    if package_path.exists():
        return package_path


def _unpack_ep(ep):
    parts: list[str] = ep.split(":")
    attr = None
    try:
        attr = parts[1]
    except IndexError:
        pass
    module_name = parts[0]
    return module_name, attr
