"""
    Resolves package, mechanism and variant constraints into asset names that can be
    requested from the Glia library.
"""

from contextlib import contextmanager

from ._fs import read_preferences, write_preferences
from .exceptions import (
    AssetLookupError,
    NoMatchesError,
    TooManyMatchesError,
    UnknownAssetError,
)


class IndexEntry:
    def __init__(self, name):
        self.name = name
        self.items = []

    def __call__(self):
        return self.items

    def __iter__(self):
        return iter(self.items)

    def __len__(self):
        return len(self.items)

    def append(self, asset):
        self.items.append(asset)


class _NoPreferenceError(Exception):
    pass


class Resolver:
    def __init__(self, manager):
        self._manager = manager
        self.global_preferences = read_preferences()
        self.local_preferences = {}
        self.__preference_stack = {}
        self.__next_stack_id = 0
        self.construct_index()

    def construct_index(self):
        packages = self._manager.packages
        self.index = {}
        self._reverse_lookup = {}
        for pkg in packages:
            for mod in pkg.mods:
                if mod.dialect is not None and mod.dialect != "neuron":
                    continue
                name = mod.asset_name
                if not name in self.index:
                    self.index[name] = IndexEntry(name)
                self.index[name].append(mod)
                self._reverse_lookup[mod.mod_name] = mod

    def resolve(self, asset_name, pkg=None, variant=None):
        if isinstance(asset_name, tuple):
            try:
                variant = asset_name[1]
                pkg = asset_name[2]
            except IndexError:
                pass
            asset_name = asset_name[0]
        if not asset_name in self.index:
            raise UnknownAssetError(
                "Selection could not be resolved: Asset '{}' not found.".format(
                    asset_name
                )
            )

        # Try resolving with preference
        resolved = self.resolve_preference(asset_name, pkg=pkg, variant=variant)
        if resolved is not None:
            return resolved.mod_name

        # If there was no preference, or if the preference couldn't resolve, try resolving
        # without preference.
        resolved = self._get_resolved(asset_name, pkg, variant)

        if not resolved:
            raise NoMatchesError(
                f"Selection {pkg}.{asset_name}.{variant} could not be resolved.",
                pkg,
                variant,
            )
        elif len(resolved) > 1:
            return self._resolve_multi(resolved, asset_name, pkg, variant).mod_name
        else:
            return resolved[0].mod_name

    def resolve_preference(self, asset_name, pkg=None, variant=None):
        # Combine global, script, context & local preferences to obtain package and variant.
        try:
            pkg, variant = self._get_final_pv(asset_name, pkg, variant)
        except _NoPreferenceError:
            # No preferences found.
            return None

        # Resolve the preferred package and variant
        resolved = self._get_resolved(asset_name, pkg, variant)
        if len(resolved) == 1:
            # Exactly 1 candidate found. Return it.
            return resolved[0]
        elif len(resolved) > 1:
            # Multiple candidates found, check if one obvious candidate stands out,
            # if not throw TooManyMatchesError.
            return self._resolve_multi(resolved, asset_name, pkg, variant)
        else:
            # No candidates found.
            return None

    def lookup(self, mod_name):
        if mod_name not in self._reverse_lookup:
            raise AssetLookupError("No mod with name '{}' found".format(mod_name))
        else:
            return self._reverse_lookup[mod_name]

    def _get_final_pv(self, asset_name, pkg, variant):
        """
        Get final package and variant preference.

        This function fetches all preferences and checks whether there's specific
        package or variant preferences. If not it checks the general package or
        variant preferences not specific to the asset.
        """
        # Fetch global, script & context preferences
        preferences = self._preferences()
        if not asset_name in preferences:
            # No specific asset preferences found, but maybe general package or variant
            # preferences apply?
            if self._has_general_preferences(preferences):
                # Get the general package and variant preferences
                p_pkg, p_variant = self._general_preferences(preferences, pkg, variant)
                if pkg is None:
                    pkg = p_pkg
                if variant is None:
                    variant = p_variant
            else:
                # No preferences of any sort found.
                raise _NoPreferenceError()
        else:
            preference = preferences[asset_name]
            if pkg is None and "package" in preference:
                pkg = preference["package"]
            if variant is None and "variant" in preference:
                variant = preference["variant"]
        return pkg, variant

    def _get_resolved(self, asset_name, pkg, variant):
        mods = iter(self.index[asset_name])
        if pkg:
            mods = filter(lambda m: m.pkg_name == pkg, mods)
        if variant:
            mods = filter(lambda m: m.variant == variant, mods)
        return list(mods)

    def _has_general_preferences(self, preferences):
        return ("__pkg" in preferences and preferences["__pkg"]) or (
            "__variant" in preferences and preferences["__variant"]
        )

    def _general_preferences(self, preferences, pkg, variant):
        return (
            pkg or (("__pkg" in preferences and preferences["__pkg"]) or None),
            variant
            or (("__variant" in preferences and preferences["__variant"]) or None),
        )

    def _resolve_multi(self, resolved, asset_name, pkg, variant):
        # If all candidates are from the same package, and 1 is the default variant
        # then return that default variant
        if all(m.pkg_name == resolved[0].pkg_name for m in resolved) and any(
            m.variant == "0" for m in resolved
        ):
            return next(m for m in resolved if m.variant == "0")
        selection = asset_name
        if pkg:
            selection = pkg + "." + asset_name
        if variant:
            selection += " ({})".format(variant)
        raise TooManyMatchesError(
            f"Selection could not be resolved, too many matches for {selection}:\n  * "
            + "\n  * ".join(r.mod_name for r in resolved)
            + "\n Try specifying a package or variant",
            list(r.mod_name for r in resolved),
            asset_name,
            pkg,
            variant,
        )

    def has_preference(self, asset_name):
        return asset_name in self._preferences()

    def set_preference(self, asset_name, glbl=False, pkg=None, variant=None):
        preference = {}
        if pkg is not None:
            preference["package"] = pkg
        if variant is not None:
            preference["variant"] = variant
        if glbl:
            self.global_preferences[asset_name] = preference
            write_preferences(self.global_preferences)
        else:
            self.local_preferences[asset_name] = preference

    @contextmanager
    def preference_context(self, assets=None, pkg=None, variant=None):
        if assets is None:
            assets = {}
        if pkg is not None:
            assets["__pkg"] = pkg
        if variant is not None:
            assets["__variant"] = variant
        id = self._stack_preference_context(assets)
        try:
            yield
        finally:
            self._pop_preference_context(id)

    def _stack_preference_context(self, assets):
        id = self.__next_stack_id
        self.__next_stack_id += 1
        self.__preference_stack[id] = assets
        return id

    def _pop_preference_context(self, id):
        del self.__preference_stack[id]

    def _preferences(self):
        pref = self.global_preferences.copy()
        pref.update(self.local_preferences)
        pref = self._apply_preference_stack(pref)
        return pref

    def _apply_preference_stack(self, base_pref):
        def combine(asset, old, new):
            if asset == "__pkg" or asset == "__variant":
                return new or old
            if "unset" in new and new["unset"]:
                old["package"] = None
                old["variant"] = None
            if "package" in new and new["package"] is not None:
                old["package"] = new["package"]
            if "variant" in new and new["variant"] is not None:
                old["variant"] = new["variant"]
            return old

        compiled_preferences = {}
        for stacked_preference in self.__preference_stack.values():
            for asset, preference in stacked_preference.items():
                if asset not in compiled_preferences:
                    if asset == "__pkg" or asset == "__variant":
                        compiled_preferences[asset] = preference
                    else:
                        compiled_preferences[asset] = {"package": None, "variant": None}
                compiled_preferences[asset] = combine(
                    asset, compiled_preferences[asset], preference
                )
        base_pref.update(compiled_preferences)
        return base_pref
