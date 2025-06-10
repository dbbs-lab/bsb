import abc
import ast
import contextlib
import inspect
import itertools
import re
import typing
from collections import defaultdict
from copy import copy
from pathlib import Path

import black

from ..assets import Mod, Package, SupportedDialect
from ..exceptions import ModSourceError, PackageApiError, PackageFileError

if typing.TYPE_CHECKING:
    from neuron.nmodl import NmodlDriver


class ModuleReferences:
    def __init__(self, module: ast.Module):
        self.module_names = []
        self.pkg_names = []
        self.mod_node = None
        self.mod_names = []
        for node in module.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "glia":
                        self.module_names.append(alias.asname or alias.name)
            elif isinstance(node, ast.ImportFrom) and node.module == "glia":
                for alias in node.names:
                    if alias.name == "Mod":
                        self.mod_names.append(alias.asname or alias.name)
                    if alias.name == "Package":
                        self.pkg_names.append(alias.asname or alias.name)
                        # Store this node to insert `Mod` import if it's missing
                        self.mod_node = node

        if not (self.module_names or self.pkg_names or self.mod_names):
            raise PackageFileError("Package file is missing top-level `glia` imports.")

    def _is_call(self, node: ast.expr, attr, aliases):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name) and func.id in aliases:
                # Class(...)
                #   or
                # ClassAlias(...)
                return True
            elif (
                isinstance(func, ast.Attribute)
                and func.attr == attr
                and isinstance(func.value, ast.Name)
                and func.value.id in self.module_names
            ):
                # glia.Class(...)
                #   or
                # gliaAlias.Class(...)
                return True
        return False

    def is_package_target(self, node: ast.expr):
        return self._is_call(node, "Package", self.pkg_names)

    def is_mod_target(self, node: ast.expr):
        return self._is_call(node, "Mod", self.mod_names)

    def make_mod_call_node(self):
        if self.mod_names:
            func = ast.Name(self.mod_names[0])
        else:
            if not self.module_names:
                # The package file does not contain a `Mod` import, and also no `import
                # glia` so it must contain a `from glia import Package`, so we can
                # append `, Mod`.
                self.mod_node.names.append(ast.alias("Mod"))
                self.mod_names.append("Mod")
                func = ast.Name("Mod")
            else:
                func = ast.Attribute(ast.Name(self.module_names[0]), ast.Name("Mod"))
        return ast.Call(func, [], [])

    def has_mod_ref(self):
        return self.mod_names or self.module_names


class PackageTransformer(ast.NodeTransformer):
    def __init__(self, path: Path, module: ast.Module, pkg_id: str):
        super().__init__()
        self._path = path
        self._module = module
        self._refs = ModuleReferences(self._module)
        self.pkg_node = self.get_package_declaration(pkg_id)

    @property
    def path(self):
        return self._path

    def get_package_declaration(self, pkg_id: str) -> ast.Call:
        pkg = None
        for node in self._module.body:
            if isinstance(node, ast.Assign):
                pkgs = [
                    n for n in node.targets if isinstance(n, ast.Name) and n.id == pkg_id
                ]
                if pkgs:
                    if pkg is not None:
                        raise PackageFileError(
                            f"Multiple top-level '{pkg_id}' assignments."
                        )
                    if len(node.targets) != 1:
                        raise PackageFileError(
                            "Tuple unpacking is not allowed "
                            "in package assigment statements."
                        )
                    if self._refs.is_package_target(node.value):
                        pkg = node.value
                    else:
                        raise PackageFileError(
                            f"Top-level assignment to '{pkg_id}' "
                            "is not a `glia.Package` declaration."
                        )
        if not pkg:
            raise PackageFileError(
                f"No top-level package declaration found for '{pkg_id}'"
            )
        return pkg

    def get_package_shim(self):
        return Package(self.get_package_name(), self._path.parent)

    def get_package_name(self):
        kw_nodes = {kw.arg: kw.value for kw in self.pkg_node.keywords}
        name_node = kw_nodes.get("name")
        if name_node is None:
            with contextlib.suppress(Exception):
                name_node = self.pkg_node.args[0]
        if name_node is None:
            raise PackageFileError(
                f"Can't find name argument in package node {ast.unparse(self.pkg_node)}"
            )
        if not isinstance(name_node, ast.Constant):
            raise PackageFileError("Package name argument must be a constant.")
        return name_node.value

    def get_modlist_declaration(self) -> ast.List:
        for keyword in self.pkg_node.keywords:
            if keyword.arg == "mods":
                modlist = keyword.value
                if not isinstance(modlist, ast.List):
                    raise PackageFileError(
                        "`mods` keyword argument must be a list statement."
                    )
                for mod in modlist.elts:
                    if not self._refs.is_mod_target(mod):
                        raise PackageFileError(
                            f"'{ast.unparse(mod)}' is not a valid `glia.Mod` declaration."
                        )
                return modlist
        raise PackageFileError("Missing `mods` keyword argument for `Package` call.")

    def get_mods(self) -> list[Mod]:
        mods = []
        for mod_call in self.get_modlist_declaration().elts:
            mod_call: ast.Call
            if any(
                not isinstance(arg, ast.Constant)
                for arg in itertools.chain(
                    mod_call.args, (v.value for v in mod_call.keywords)
                )
            ):
                raise PackageFileError(
                    "Mod declarations may only use constant arguments."
                )
            mod_node = copy(mod_call)
            mod_node.func = ast.Name("Mod")
            mod_str = ast.unparse(mod_node)
            self.get_package_name()
            pkg = self.get_package_shim()
            try:
                mod = eval(mod_str, {"Mod": Mod})
                mod.set_package(pkg)
                mods.append(mod)
            except Exception as e:
                raise PackageFileError(
                    f"`{mod_str}` is not a valid glia.Mod declaration."
                ) from e
        return mods

    def add_mod(self, mod: Mod):
        modlist = self.get_modlist_declaration()
        modlist.elts.append(self.make_mod_node(mod))

    def make_mod_node(self, mod: Mod):
        call = self._refs.make_mod_call_node()
        for param in inspect.signature(Mod).parameters.values():
            try:
                value = getattr(mod, param.name)
            except AttributeError:
                raise PackageApiError(
                    f"Can't read attribute `Mod.{param.name}`."
                ) from None
            # Convert non-constants to string, otherwise `ast.Constant` calls `__repr__`
            # and can create invalid runtime code
            if type(value) not in (str, bool, int, float, type(None)):
                value = str(value)
            # Omit default parameter values
            if value == param.default:
                continue
            if param.kind == inspect.Parameter.POSITIONAL_OR_KEYWORD:
                call.args.append(ast.Constant(value))
            elif param.kind == inspect.Parameter.KEYWORD_ONLY:
                call.keywords.append(ast.keyword(param.name, ast.Constant(value)))
            else:
                raise PackageApiError("Couldn't process glia.Mod class arguments.")
        return call

    def write_in_place(self):
        self._path.write_text(
            black.format_file_contents(
                ast.unparse(self._module),
                fast=True,
                mode=black.Mode(),
            )
        )


def get_package_transformer(path: Path, pkg_id: str):
    module = ast.parse(path.read_text(), str(path))
    return PackageTransformer(path, module, pkg_id)


class NmodlWriter:
    def __init__(self, mod: Mod):
        self._mod = mod
        self._source = None
        self._driver: NmodlDriver = None

    @property
    def nmodl(self):
        try:
            import neuron.nmodl
            import neuron.nmodl.ast
            import neuron.nmodl.dsl
            import neuron.nmodl.visitor

            return neuron.nmodl
        except ImportError as e:
            raise RuntimeError(
                "`nmodl` package unavailable. Please install NEURON. If you are on "
                "Windows, please see https://github.com/neuronsimulator/nrn/issues/3432"
            ) from e

    def parse_source(self, source: Path, dialect: SupportedDialect = None):
        text = source.read_text()
        for patch in get_patches(dialect):
            text = patch.common(text)
        self._source = self.nmodl.NmodlDriver().parse_string(text)

    def update_suffix_ast(self, name=None):
        if name is None:
            name = self._mod.mod_name
        self._check_source()
        visitor = self.nmodl.visitor.AstLookupVisitor()
        block = visitor.lookup(self._source, self.nmodl.ast.AstNodeType.NEURON_BLOCK)
        statements = [
            st for st in block[0].statement_block.statements if not st.is_suffix()
        ]
        if self._mod.is_artificial_cell:
            suffix = "ARTIFICIAL_CELL"
        elif self._mod.is_point_process:
            suffix = "POINT_PROCESS"
        else:
            suffix = "SUFFIX"

        statements.insert(
            0,
            self.nmodl.ast.Suffix(
                self.nmodl.ast.Name(self.nmodl.ast.String(suffix)),
                self.nmodl.ast.Name(self.nmodl.ast.String(name)),
            ),
        )
        block[0].statement_block.statements = statements

    def import_source(self, source: Path, dest: Path, dialect: SupportedDialect = None):
        mod_path = (dest / self._mod.relpath).resolve()
        mod_path.parent.mkdir(parents=True, exist_ok=True)
        # Import dialect source
        self.parse_source(source, dialect=dialect)
        self.update_suffix_ast()
        # Write common source
        self.write(mod_path)

    def write(self, target: Path, dialect: SupportedDialect = None):
        self._check_source()
        text = self.nmodl.to_nmodl(self._source)
        for patch in get_patches(dialect):
            text = patch.dialect(text)
        target.write_text(text)

    def extract_source_info(self):
        self._check_source()
        visitor = self.nmodl.visitor.AstLookupVisitor()
        suffixes = visitor.lookup(self._source, self.nmodl.ast.AstNodeType.SUFFIX)
        if len(suffixes) > 1:
            raise ModSourceError(
                "Multiple SUFFIX, POINT_PROCESS, or ARTIFICIAL_CELL statements detected."
            )
        elif not suffixes:
            self._mod.is_artificial_cell = False
            self._mod.is_point_process = False
        else:
            value = str(suffixes[0].type.value)
            self._mod.is_artificial_cell = value == "ARTIFICIAL_CELL"
            self._mod.is_point_process = value == "POINT_PROCESS"

    def _check_source(self):
        if self._source is None:
            raise RuntimeError(f"No nmodl source set for {self._mod}")


_patches = defaultdict(list)


class DialectPatch(abc.ABC):
    @abc.abstractmethod
    def dialect(self, common_text: str) -> str:
        pass

    @abc.abstractmethod
    def common(self, dialect_text: str) -> str:
        pass

    def __init_subclass__(cls, dialect: SupportedDialect, **kwargs):
        super().__init_subclass__(**kwargs)
        register_patch(dialect, cls())


def register_patch(dialect: SupportedDialect, patch: DialectPatch):
    _patches[dialect].append(patch)


def get_patches(dialect: SupportedDialect) -> list[DialectPatch]:
    return _patches[dialect]


class UniDirEqPatch(DialectPatch, dialect="arbor"):
    """
    Replace arbor's `a <-> (0, f)` with NMODL's `a << f`.
    """

    dialect_regex = re.compile(r"~\s*(\w+)\s*<->\s*\(\s*0\s*,\s*(.+)\)")
    common_regex = re.compile(r"~\s*(\w+)\s*<<\s*\((.+)\)")

    def dialect(self, common_text: str) -> str:
        return self.common_regex.sub(r"~ \1 <-> (0, \2)", common_text)

    def common(self, dialect_text: str) -> str:
        return self.dialect_regex.sub(r"~ \1 << (\2)", dialect_text)


class IndependentPatch(DialectPatch, dialect="neuron"):
    """
    Strip INDEPENDENT blocks: does nothing and NMODL parses them incorrectly.
    """

    regex = re.compile(r"INDEPENDENT\s*\{.+?\}", re.DOTALL)

    def dialect(self, common_text: str) -> str:
        return common_text

    def common(self, dialect_text: str) -> str:
        return self.regex.sub("", dialect_text)
