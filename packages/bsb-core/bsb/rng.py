"""
Configured randomness.

Two things have to be true at once, and they are independent of each other.

Running one configuration repeatedly must give **technical replicates**: runs that
differ only in their randomness. Taking the configuration back out of a run's output
and running it again must **reproduce** that run exactly. The two configurations then
differ in nothing but seed values, because an unset seed is drawn and written down.

Separately, a run must not depend on how its work was divided. Draws are therefore
seeded from *what is being drawn for* -- a chunk, a cell type, a device -- and never
from the MPI rank, so the same configuration gives the same result whatever the rank
count.
"""

import typing

import numpy as np

from . import config
from .config import types
from .config._attrs import cfgdict
from .config._make import get_config_attributes
from .exceptions import ConfigurationError

if typing.TYPE_CHECKING:  # pragma: nocover
    from .core import Scaffold


def _mark_written(node, attr_name: str) -> None:
    """
    Record a resolved value as though it had been configured.

    A seed that was drawn rather than written has to reach the stored configuration,
    or the run it belongs to cannot be reproduced. Serialisation only walks what was
    written, so a drawn seed says so.
    """
    if node is None:
        return
    attr = get_config_attributes(type(node)).get(attr_name)
    if attr is not None:
        attr.flag_dirty(node)


def _stable_ints(key) -> list[int]:
    """
    Turn a derivation key into integers, stably across processes and runs.

    Python's own ``hash`` is salted per process, so a string hashed with it would
    seed differently on every invocation and silently break reproducibility.
    """
    import zlib

    parts: list[int] = []
    for element in key if isinstance(key, tuple | list) else (key,):
        if isinstance(element, str):
            parts.append(zlib.crc32(element.encode()))
        elif isinstance(element, bool | int | np.integer):
            parts.append(int(element))
        elif isinstance(element, tuple | list | np.ndarray):
            parts.extend(_stable_ints(tuple(element)))
        elif element is None:
            parts.append(0)
        else:
            parts.append(zlib.crc32(repr(element).encode()))
    return parts


@config.node
class RandomProvider:
    """
    One source of randomness, and the seed it was given or drawn.
    """

    name: str = config.attr(key=True)

    seed: int = config.attr(type=types.int(), required=False)
    """
    Seed for this provider. Left unset, it is derived from the root seed when the
    configuration is booted, and written back so the run can be reproduced.
    """

    def __boot__(self):
        self.resolve()

    def resolve(self) -> int:
        """
        Settle this provider's seed, deriving it from the root when it has none.

        :returns: The resolved seed.
        """
        if self.seed is None:
            root = self._config_parent._config_parent
            self.seed = int(
                np.random.SeedSequence(
                    [root.resolve_seed(), *_stable_ints(self.name)]
                ).generate_state(1, dtype=np.uint32)[0]
            )
        return self.seed


@config.node
class RandomNode:
    """
    The :guilabel:`rng` block: a root seed, and providers that derive from it.

    Leave :attr:`seed` unset and every run is a replicate, each output carrying the
    seed it used. Set it -- or paste back the one a run recorded -- and that run
    reproduces exactly. Pin a single provider to hold one part of a model fixed
    while the rest varies.
    """

    scaffold: "Scaffold"

    seed: int = config.attr(type=types.int(), required=False)
    """
    Root seed every provider derives from. Left unset, one is drawn when the
    configuration is booted and written back, so the run can be reproduced by
    feeding the stored configuration back in.
    """

    providers: cfgdict[str, RandomProvider] = config.dict(type=RandomProvider)
    """
    Individual sources of randomness. An entry with its own :guilabel:`seed` is
    held fixed; one without derives from :attr:`seed` like everything else.
    """

    def __boot__(self):
        self.resolve_seed()
        for provider in self.providers.values():
            provider.resolve()
        # The block itself has to be recorded as configured, or a drawn seed would
        # resolve in memory and never reach the stored configuration.
        _mark_written(self._config_parent, "rng")

    def resolve_seed(self) -> int:
        """
        Settle the root seed, drawing one if none was configured.

        Drawn from the operating system rather than from a fixed default, so an
        unseeded configuration is a fresh replicate every time, and written back so
        the stored configuration reproduces this run.

        :returns: The resolved root seed.
        """
        if self.seed is None:
            self.seed = int(np.random.SeedSequence().entropy % (2**32))
        return self.seed

    def get_rng(self, provider: str = "bsb", key=()) -> np.random.Generator:
        """
        A generator for one particular set of draws.

        ``key`` is what the draws are *for* -- a chunk, a cell type, a device, a
        connection tag. Two calls with the same key give the same stream, and a key
        never includes the MPI rank, so which rank happens to do the work cannot
        change the result.

        :param provider: Name of the provider to draw from. Unknown names derive
            from the root seed like any unpinned provider.
        :param key: What the draws are for. Strings, integers and nested sequences
            of them are all hashed stably.
        :returns: A seeded generator.
        """
        if provider in self.providers:
            seed = self.providers[provider].resolve()
        else:
            seed = int(
                np.random.SeedSequence(
                    [self.resolve_seed(), *_stable_ints(provider)]
                ).generate_state(1, dtype=np.uint32)[0]
            )
        return np.random.default_rng(np.random.SeedSequence([seed, *_stable_ints(key)]))


def get_rng(obj, provider: str = "bsb", key=()) -> np.random.Generator:
    """
    Draw from a scaffold's configured randomness, from anywhere that can reach one.

    :param obj: A scaffold, or any configuration node booted into one.
    :param provider: Name of the provider to draw from.
    :param key: What the draws are for; see :meth:`RandomNode.get_rng`.
    :returns: A seeded generator.
    """
    scaffold = getattr(obj, "scaffold", obj)
    if scaffold is None or not hasattr(scaffold, "configuration"):
        raise ConfigurationError(
            f"Cannot draw randomness from {obj!r}: it is not attached to a network."
        )
    return scaffold.configuration.rng.get_rng(provider, key)


__all__ = ["RandomNode", "RandomProvider", "get_rng"]
