"""
NMODL Asset Manager for Arbor and NEURON.

~ Glues your neurons together!

Manage a local NMODL library that's automatically compiled, loaded, and
recompiled whenever you change your NMODL code or simulator environment.
"""

from ._fs import get_cache_path as _get_cache_path
from ._glia import Glia, MechId
from .assets import Catalogue, Mod, Package
from .exceptions import (
    AssetLookupError,
    BuildCatalogueError,
    CatalogueError,
    CompileError,
    GliaError,
    LibraryError,
    ModSourceError,
    NeuronError,
    NmodlError,
    NoMatchesError,
    PackageApiError,
    PackageError,
    PackageFileError,
    PackageModError,
    PackageProjectError,
    PackageVersionError,
    ResolveError,
    TooManyMatchesError,
    UnknownAssetError,
)
from .neuron import MechAccessor

_manager = Glia()


def insert(section, asset, variant=None, pkg=None, /, attributes=None, x=None):
    """
    Insert a mechanism or point process into a Section.

    :param section: The section to insert the asset into.
    :type section: patch.objects.Section
    :param asset: The name of the asset. Will be resolved into a fully qualified
       NEURON name based on preferences, unless a fully qualified name is given.

    :type asset: str
    :param attributes: Attributes of the asset to set on the section/mechanism.
    :type attributes: dict
    :param pkg: Package preference. Overrides global & script preferences.
    :type pkg: str
    :param variant: Variant preference. Overrides global & script preferences.
    :type variant: str
    :param x: Position along the `section` to place the point process at. Does
       not apply to mechanisms.

    :type x: float
    :raises: LibraryError if the asset isn't found or was incorrectly marked as
       a point process.
    """
    return _manager.insert(section, asset, variant, pkg, attributes, x)


def resolve(asset, pkg=None, variant=None):
    """
    Resolve an asset selection command to the name known to NEURON.
    """
    return _manager.resolve(asset, pkg=pkg, variant=variant)


def select(asset, pkg=None, variant=None):
    """
    Set script scope preferences for an asset.

    :param asset: Unresolved asset name.
    :type asset: str
    :param pkg: Name of the package to prefer.
    :type pkg: str
    :param variant: Name of the variant to prefer.
    :type variant: str
    """
    return _manager.select(asset, pkg=pkg, variant=variant)


def compile():
    """
    Compile and test all mod files found in all Glia packages.
    """
    return _manager.compile()


def load_library():
    """
    Load the glia library (if it isn't loaded yet).
    """
    return _manager.load_library()


def context(assets=None, pkg=None, variant=None):
    """
    Creates a context that sets glia preferences during a `with` statement.
    """
    return _manager.context(assets=assets, pkg=pkg, variant=variant)


def catalogue(name):
    """
    Load or build an Arbor mechanism catalogue.

    :param name: Name of the Glia installed Arbor catalogue.
    :type name: str
    """
    return _manager.catalogue(name)


def package(name):
    """
    Return package.

    :param name: Name of the installed glia package.
    :type name: str
    """
    return _manager.package(name)


def get_packages():
    """
    Return all installed packages.
    """
    return [*_manager.packages]


def get_cache_path():
    """
    Get the cache path where intermediary files are stored.

    Glia also stores a JSON cache in another directory, which
    you won't find here, but ``glia cache --clear`` can reset.
    """
    return _get_cache_path()


__all__ = [
    "AssetLookupError",
    "BuildCatalogueError",
    "Catalogue",
    "CatalogueError",
    "CompileError",
    "GliaError",
    "LibraryError",
    "MechAccessor",
    "MechId",
    "Mod",
    "ModSourceError",
    "NeuronError",
    "NmodlError",
    "NoMatchesError",
    "Package",
    "PackageApiError",
    "PackageError",
    "PackageFileError",
    "PackageModError",
    "PackageProjectError",
    "PackageVersionError",
    "ResolveError",
    "TooManyMatchesError",
    "UnknownAssetError",
]
