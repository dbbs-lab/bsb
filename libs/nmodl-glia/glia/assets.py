import contextlib
import os
import shutil
import subprocess
import typing
from pathlib import Path
from tempfile import TemporaryDirectory, mkdtemp

from . import _mpi
from ._fs import get_cache_path, read_cache, update_cache
from ._hash import get_package_hash, get_package_mods_hash
from .exceptions import *

if typing.TYPE_CHECKING:
    import arbor


SupportedDialect = typing.Union[typing.Literal["arbor"], typing.Literal["neuron"]]


class _ModList(list):
    def __init__(self, package: "Package", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pkg = package
        for item in self:
            if not isinstance(item, Mod):
                raise PackageFileError(f"Package mod '{item}' is not a valid `glia.Mod`.")
            item.set_package(package)

    def __setitem__(self, key, value):
        if not isinstance(value, Mod):
            raise PackageFileError(f"Package mod '{value}' is not a valid `glia.Mod`.")
        super().__setitem__(key, value)
        value.set_package(self.pkg)

    def append(self, item):
        item.set_package(self.pkg)
        super().append(item)

    def extend(self, itr):
        super().extend(i.set_package(self.pkg) or i for i in itr)


class Package:
    def __init__(self, name: str, root: Path, *, mods: list["Mod"] = None, builtin=False):
        self._name = name
        self._root = Path(root)
        self.mods: list["Mod"] = _ModList(self, [] if mods is None else mods)
        # Exceptional flag for the NEURON builtins.
        # They need a definition to be `insert`ed,
        # but have no mod files to be compiled.
        self.builtin = builtin

    @property
    def name(self):
        return self._name

    @property
    def catalogue(self):
        return Catalogue(self)

    @property
    def hash(self):
        return get_package_hash(self)

    @property
    def mod_hash(self):
        return get_package_mods_hash(self)

    @property
    def root(self):
        return self._root

    def load_catalogue(self) -> "arbor.catalogue":
        return self.catalogue.load()

    def build_catalogue(self, *args, **kwargs) -> "arbor.catalogue":
        return self.catalogue.build(*args, **kwargs)

    def get_mods(self, dialect=None) -> list["Mod"]:
        # Find common mods
        mods = {mod.mod_name: mod for mod in self.mods if mod.dialect is None}
        if dialect:
            # Overwrite with dialect-specific mods
            mods.update(
                (mod.mod_name, mod) for mod in self.mods if mod.dialect == dialect
            )
        return [*mods.values()]


class Mod:
    def __init__(
        self,
        relpath: str,
        asset_name,
        *,
        variant="0",
        is_point_process=False,
        is_artificial_cell=False,
        dialect: SupportedDialect = None,
        builtin=False,
    ):
        self._pkg: typing.Optional[Package] = None
        self.relpath = relpath
        self.asset_name = asset_name
        self.variant = variant
        self.is_point_process = is_point_process
        self.is_artificial_cell = is_artificial_cell
        self.dialect = dialect
        self.builtin = builtin

    def set_package(self, package: Package):
        self._pkg = package

    @property
    def pkg(self):
        return self._pkg

    @property
    def pkg_name(self):
        return self._pkg.name

    @property
    def mech_id(self):
        return ModName(self.pkg_name, self.asset_name, self.variant).mech_id

    @property
    def mod_name(self):
        if self.builtin:
            return self.asset_name
        return ModName(self.pkg_name, self.asset_name, self.variant).full_mod_name

    @property
    def arbor_name(self):
        return ModName(self.pkg_name, self.asset_name, self.variant).arbor_mod_name

    @property
    def path(self) -> Path:
        return self.pkg.root / self.relpath


class ModName:
    def __init__(self, pkg_name: str, asset: str, variant: str):
        self.pkg = pkg_name
        self.asset = asset
        self.variant = variant

    @property
    def full_mod_name(self):
        if self.pkg is None:
            raise ValueError("Missing pkg info for mod name.")
        else:
            return f"glia__{self.pkg}__{self.asset}__{self.variant}"

    @property
    def short_mod_name(self):
        return f"{self.asset}__{self.variant}"

    @property
    def arbor_mod_name(self):
        name = self.asset
        if self.variant and self.variant != "0":
            name += "_" + self.variant
        return name

    @classmethod
    def parse(cls, name: str):
        name_parts = name.split("__")
        if len(name_parts) == 2:
            return cls(None, *name_parts)
        elif len(name_parts) == 4:
            return cls(*name_parts[1:])
        else:
            raise ValueError(f"Unparsable mod name '{name}'.")

    @classmethod
    def parse_path(cls, path: str):
        return cls.parse(Path(path).stem)

    @property
    def mech_id(self):
        if not self.variant:
            return self.asset
        elif not self.pkg:
            return (self.asset, self.variant)
        else:
            return (self.asset, self.variant, self.pkg)


class Catalogue:
    def __init__(self, package: Package):
        self._pkg = package
        self._cache = get_cache_path(self.name, prefix="arb_")

    @property
    def name(self):
        return self._pkg.name

    def load(self) -> "arbor.catalogue":
        import arbor

        if not self.is_fresh():
            self.build()
        return arbor.load_catalogue(self._get_library_path())

    def _get_library_path(self):
        return os.path.join(self._cache, f"{self.name}-catalogue.so")

    def is_fresh(self):
        if not os.path.exists(self._get_library_path()):
            return False
        try:
            cache_data = read_cache()
            cached = cache_data.get("cat_hashes", {}).get(self.name, None)
            return cached == self._hash()
        except FileNotFoundError as _:
            return False

    def _hash(self):
        import arbor

        arbor_hash = str(arbor.config())
        return self._pkg.mod_hash + arbor_hash

    def build(self, verbose=None, debug=False, gpu=None):
        # Turn verbosity on if debug is on, unless it's explicitly toggled off.
        verbose = False if verbose is False else verbose or debug

        def run_build():
            self._build_local(verbose, debug, gpu)

        build_err = None
        try:
            if _mpi.main_node:
                run_build()
        except Exception as err:
            _mpi.bcast(err)
            raise err from None
        else:
            build_err = _mpi.bcast(build_err)
            if build_err:
                raise BuildCatalogueError(
                    "Catalogue build error, look for main node error."
                ) from None

    def _build_local(self, verbose, debug, gpu):
        tmp_dir = TemporaryDirectory
        if debug:
            # Temp dir context manager that doesn't clean up the build folder so that
            # the generated cpp code can be debugged
            class TmpDir:
                def __enter__(*args, **kwargs):
                    return mkdtemp()

                def __exit__(*args, **kwargs):
                    pass

            tmp_dir = TmpDir

        with self.assemble_arbor_mod_dir() as mod_path:
            with tmp_dir() as tmp:
                pwd = os.getcwd()
                os.chdir(tmp)
                try:
                    cmd = f"arbor-build-catalogue {self.name} {mod_path}"
                    subprocess.run(
                        cmd
                        + (" --quiet" if not verbose else "")
                        + (" --verbose" if verbose else "")
                        + (" --debug" if debug else "")
                        + (f" --gpu={gpu}" if gpu else ""),
                        shell=True,
                        check=True,
                        capture_output=not verbose,
                    )
                except subprocess.CalledProcessError as e:
                    msg_p = [f"ABC errored out with exitcode {e.returncode}"]
                    if verbose:
                        msg_p += ["Check log above for error."]
                    else:
                        msg_p += [
                            f"Command: {cmd}\n---- ABC output ----",
                            e.stdout.decode(),
                            "---- ABC error  ----",
                            e.stderr.decode(),
                        ]
                    msg = "\n\n".join(msg_p)
                    raise BuildCatalogueError(msg) from None
                else:
                    os.makedirs(self._cache, exist_ok=True)
                    shutil.copy2(f"{self.name}-catalogue.so", self._cache)
                finally:
                    os.chdir(pwd)
        if debug:
            print(f"Debug copy of catalogue in '{tmp}'")
        # Cache directory hash of current mod files so we only rebuild on source code
        # changes.
        cache_data = read_cache()
        cat_hashes = cache_data.setdefault("cat_hashes", dict())
        cat_hashes[self.name] = self._hash()
        update_cache(cache_data)

    @contextlib.contextmanager
    def assemble_arbor_mod_dir(self):
        from .packaging import NmodlWriter

        with TemporaryDirectory() as tmpdir:
            for mod in self._pkg.get_mods(dialect="arbor"):
                writer = NmodlWriter(mod)
                writer.parse_source(mod.path)
                # `arbor-build-catalogue` needs filename to match suffix statement.
                # See https://github.com/arbor-sim/arbor/issues/2250
                writer.update_suffix_ast(mod.arbor_name)
                writer.write(
                    (Path(tmpdir) / mod.arbor_name).with_suffix(".mod"), dialect="arbor"
                )
            yield tmpdir
