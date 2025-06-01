from errr.tree import exception as _e
from errr.tree import make_tree as _make_tree

_make_tree(
    globals(),
    GliaError=_e(
        CompileError=_e(),
        LibraryError=_e(),
        NeuronError=_e(),
        ResolveError=_e(
            TooManyMatchesError=_e("matches", "asset", "pkg", "variant"),
            NoMatchesError=_e("pkg", "variant"),
            UnknownAssetError=_e(),
            AssetLookupError=_e(),
        ),
        PackageError=_e(
            PackageApiError=_e(),
            PackageFileError=_e(),
            PackageModError=_e(),
            PackageProjectError=_e(),
            PackageVersionError=_e(),
        ),
        CatalogueError=_e(BuildCatalogueError=_e()),
        NmodlError=_e(ModSourceError=_e()),
    ),
)

GliaError: type[Exception]
CompileError: type[GliaError]  # noqa: F821
LibraryError: type[GliaError]  # noqa: F821
NeuronError: type[GliaError]  # noqa: F821
ResolveError: type[GliaError]  # noqa: F821
TooManyMatchesError: type[ResolveError]  # noqa: F821
NoMatchesError: type[ResolveError]  # noqa: F821
UnknownAssetError: type[ResolveError]  # noqa: F821
AssetLookupError: type[ResolveError]  # noqa: F821
PackageError: type[GliaError]  # noqa: F821
PackageApiError: type[PackageError]  # noqa: F821
PackageFileError: type[PackageError]  # noqa: F821
PackageModError: type[PackageError]  # noqa: F821
PackageProjectError: type[PackageError]  # noqa: F821
PackageVersionError: type[PackageError]  # noqa: F821
CatalogueError: type[GliaError]  # noqa: F821
BuildCatalogueError: type[CatalogueError]  # noqa: F821
NmodlError: type[GliaError]  # noqa: F821
ModSourceError: type[NmodlError]  # noqa: F821


class PackageWarning(Warning):
    pass
