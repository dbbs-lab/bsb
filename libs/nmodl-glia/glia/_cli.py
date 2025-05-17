import shutil
from pathlib import Path

import click

from . import _manager, _mpi
from ._fs import clear_cache, get_cache_path, get_local_pkg_path
from ._local import create_local_package
from .assets import ModName
from .exceptions import *
from .packaging import PackageManager


@click.group()
def glia():
    pass


@glia.command(help="Compile the Glia library")
def compile():
    if _mpi.main_node:
        click.echo("Glia is compiling...")
    _manager.compile()
    if _mpi.main_node:
        click.echo("Compilation complete!")
    assets, _ = _manager._precompile_cache()
    if _mpi.main_node:
        click.echo(
            "Compiled assets: "
            + ", ".join(
                set(f"{mod.pkg.name}.{mod.asset_name}({mod.variant})" for mod in assets)
            ),
        )
        click.echo("Testing assets ...")
    test(_manager.resolver.index.keys())


@glia.command("list", help="List installed components")
def list_assets():
    click.echo(
        "Assets: "
        + ", ".join(f"{e.name} ({len(e)})" for e in _manager.resolver.index.values()),
    )
    click.echo("Packages: " + ", ".join(p.name for p in _manager.packages))


@glia.command(help="Set global preferences for an asset.")
@click.argument("asset")
@click.option("-p", "--package", default=None, help="Package preference for this asset")
@click.option("-v", "--variant", default=None, help="Variant preference for this asset")
def select(asset, package, variant):
    _manager.select(asset, pkg=package, variant=variant, glbl=True)


@glia.command(help="Print info on an asset.")
@click.argument("asset")
def show(asset):
    index = _manager.resolver.index
    preferences = _manager.resolver._preferences()
    if not asset in index:
        raise click.exceptions.BadArgumentUsage(f'Unknown ASSET "{asset}"')
    if asset in preferences:
        preference = preferences[asset]
        pref_mod = None
        try:
            pref_mod = _manager.resolver.resolve_preference(asset)
        except ResolveError as e:
            click.echo("resolve error" + e)
            pass
        pref_string = ""
        if "package" in preference:
            pref_string += "pkg=" + preference["package"] + " "
        if "variant" in preference:
            pref_string += "variant=" + preference["variant"] + " "
        click.echo("Current preferences: " + pref_string)
        click.echo("Current preferred module:" + pref_mod.mod_name)
    click.echo("Available modules:")
    for mod in _manager.resolver.index[asset]:
        click.echo("  *" + mod.mod_name)


@glia.command(help="Print info on a package.")
@click.argument("package")
def show_pkg(package):
    candidates = [p for p in _manager.packages if p.name.find(package) != -1]
    if not len(candidates):
        raise click.exceptions.BadArgumentUsage(f'Unknown PACKAGE "{package}"')
    for candidate in candidates:
        click.echo("Package: " + click.style(candidate.name, fg="green"))
        click.echo("=====")
        click.echo(f"Location: {candidate.root}")
        click.echo()
        click.echo("Available modules:")
        for mod in candidate.mods:
            click.echo(f"  * {mod.mod_name} = {mod.path}")
        click.echo()


@glia.command(help="Test mechanisms")
@click.argument("mechanisms", nargs=-1)
def test(mechanisms, verbose=False):
    if len(mechanisms) == 0:
        mechanisms = _manager.resolver.index.keys()
    successes = 0
    tests = len(mechanisms)
    ecode = 0
    for mechanism in mechanisms:
        mstr = "[OK]"
        estr = ""
        try:
            _manager.test_mechanism(mechanism)
            successes += 1
        except LibraryError as e:
            mstr = "[ERROR]"
            estr = str(e)
            ecode = 1
        except UnknownAssetError as _:
            mstr = "[?]"
            ecode = 1
        except TooManyMatchesError as e:
            mstr = "[MULTI]"
            estr = str(e)
        except AssetLookupError as e:
            mstr = "[X]"
            estr = str(e)
        click.echo(f"{mstr} {mechanism}")
        if verbose and estr != "":
            click.echo("  -- " + estr)
    if _mpi.main_node:
        click.echo(f"Tests finished: {successes} out of {tests} passed")
    exit(ecode)


@glia.command(help="Build an Arbor catalogue")
@click.argument("catalogue")
@click.option(
    "-v", "--verbose", is_flag=True, default=False, help="Show catalogue build output."
)
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    default=False,
    help="Build in debug mode to inspect build intermediates.",
)
@click.option("--gpu/--cpu", default=False, help="Build catalogue for GPU.")
def build(catalogue, verbose, debug, gpu):
    _manager.build_catalogue(catalogue, verbose=verbose, debug=debug, gpu=gpu)


@glia.command(help="Show or clear the cache path used in the current environment")
@click.option(
    "--clear",
    is_flag=True,
    default=False,
    help="Clear the cached JSON data and cache directory.",
)
def cache(clear):
    click.echo(get_cache_path())
    if clear:
        clear_cache()
        shutil.rmtree(get_cache_path())


@glia.group(help="All commands related to packaging your NMODL files for others")
def pkg():
    pass


@pkg.command(help="Create a new Glia package.")
def new():
    from cookiecutter.main import cookiecutter

    cookiecutter(
        str((Path(__file__).parent / "packaging/cookiecutter-glia").resolve()),
    )


def _guess_name(ctx, param, value):
    if value == param.default:
        try:
            name = ModName.parse_path(ctx.params["source"])
            if param.name == "name":
                value = name.asset
            elif param.name == "variant":
                value = name.variant
            else:
                raise RuntimeError("_guess_name used for wrong option.")
        except ValueError:
            value = click.prompt(param.name.title(), type=str)
    return value


@pkg.command(help="Add a mod file to the current package.")
@click.argument(
    "source",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "-w",
    "--overwrite",
    is_flag=True,
    default=False,
    help="Whether to overwrite if NMODL file exists at target location",
)
@click.option("-n", "--name", type=str, callback=_guess_name, help="The asset name")
@click.option(
    "-t",
    "--target",
    default=None,
    type=click.Path(dir_okay=True, path_type=Path),
    help="The path relative to the package root to place the mod file.",
)
@click.option(
    "-v",
    "--variant",
    default="0",
    type=str,
    callback=_guess_name,
    help="The asset variant",
)
@click.option(
    "-l",
    "--local",
    is_flag=True,
    default=False,
    help="Add the NMODL asset to your local library",
)
@click.option(
    "-a",
    "--arbor",
    "dialect",
    flag_value="arbor",
    help="Restrict the usage of this NMODL file to the Arbor dialect.",
)
@click.option(
    "-n",
    "--neuron",
    "dialect",
    flag_value="neuron",
    help="Restrict the usage of this NMODL file to the NEURON dialect.",
)
def add(source, name, variant, overwrite, target, local, dialect):
    path = Path(get_local_pkg_path() if local else ".")
    if local and not path.exists():
        create_local_package()
    pkg = PackageManager(path)
    mod_path = pkg.get_mod_dir(target)
    if mod_path.is_dir():
        mod_path /= f"{name}__{variant}.mod"
    if dialect and not target:
        # If the target isn't manually specified, splice in the dialect path.
        mod_path = mod_path.parent / dialect / mod_path.name
    if not overwrite and mod_path.exists():
        raise FileExistsError(f"Target mod file '{mod_path.resolve()}' already exists.")
    mod = pkg.get_mod_from_source(source, name=name, variant=variant, dialect=dialect)
    mod.relpath = pkg.get_rel_path(mod_path)
    mod.dialect = dialect
    pkg.add_mod_file(source, mod)


@pkg.command(help="Check for integrity problems with the package")
def check():
    pass
