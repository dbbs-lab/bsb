"""
Configured randomness.

Two things have to be true at once, and they are independent of each other.

Running one configuration repeatedly must give **technical replicates**: runs that
differ only in their randomness. Taking the configuration back out of a run's output
and running it again must **reproduce** that run exactly. The two configurations then
differ in nothing but seed values, because an unset seed is drawn and written down.

Separately, a run must not depend on how its work was divided. Draws are therefore
seeded from *what is being drawn for*, such as a chunk, a cell type or a device,
and never from the MPI rank, so the same configuration gives the same result
whatever the rank count.

The :guilabel:`rng` block is itself the generator everything draws from unless it says
otherwise, and it registers two kinds of named node beside it: :guilabel:`generators`,
which are drawn from, and :guilabel:`settings`, which are handed to a subsystem that
seeds itself. A component names one through its own :guilabel:`rng` attribute, so what
it draws from stands in the configuration rather than being looked up by a string at
runtime.
"""

import abc
import typing
import zlib

import numpy as np

from . import config
from .config import refs, types
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


# Tags the element kinds apart, so a value never shares an encoding with one of
# another kind: `None` is not the integer 0, and `False` is not either.
_KEY_NONE, _KEY_BOOL, _KEY_INT, _KEY_STR, _KEY_SEQ, _KEY_OBJ = range(6)


def _zigzag(value: int) -> int:
    """
    Fold a signed integer onto the non-negative ones a seed sequence accepts.

    Chunk coordinates go negative, and a negative is rejected outright rather than
    hashed.
    """
    return 2 * value if value >= 0 else -2 * value - 1


def _encode_key(key) -> list[int]:
    parts: list[int] = []
    for element in key if isinstance(key, tuple | list) else (key,):
        if isinstance(element, str):
            parts += [_KEY_STR, zlib.crc32(element.encode())]
        elif isinstance(element, bool):
            parts += [_KEY_BOOL, int(element)]
        elif isinstance(element, int | np.integer):
            parts += [_KEY_INT, _zigzag(int(element))]
        elif isinstance(element, tuple | list | np.ndarray):
            nested = _encode_key(tuple(element))
            parts += [_KEY_SEQ, len(nested), *nested]
        elif element is None:
            parts += [_KEY_NONE]
        else:
            parts += [_KEY_OBJ, zlib.crc32(repr(element).encode())]
    return parts


def _stable_ints(key) -> list[int]:
    """
    Turn a derivation key into integers, stably across processes and runs.

    Python's own ``hash`` is salted per process, so a string hashed with it would
    seed differently on every invocation and silently break reproducibility.

    The encoding leads with its own length, because a seed sequence absorbs a
    trailing zero: without it a key ending in one hashes the same as the key
    without that element at all.
    """
    parts = _encode_key(key)
    return [len(parts), *parts]


def _bit_generators() -> dict[str, type]:
    """Every bit generator :mod:`numpy` offers, by name."""
    return {
        name: attr
        for name in dir(np.random)
        if isinstance(attr := getattr(np.random, name, None), type)
        and issubclass(attr, np.random.BitGenerator)
        and attr is not np.random.BitGenerator
    }


def _bit_generator(value):
    """
    Resolve a bit generator by name, at configuration time.

    :mod:`numpy` carries plenty of names that are not bit generators, and a name that
    is not one at all reads the same in a configuration file, so both are caught here
    rather than at the first draw somewhere else entirely.
    """
    known = _bit_generators()
    if value in known:
        return value
    raise TypeError(
        f"'{value}' is not a numpy bit generator, pick one of: "
        f"{', '.join(sorted(known))}."
    )


_bit_generator.__name__ = "a numpy bit generator"


def _derive(seed: int, key) -> int:
    """One reproducible 32 bit integer for ``key``, out of ``seed``."""
    sequence = np.random.SeedSequence([seed, *_stable_ints(key)])
    return int(sequence.generate_state(1, dtype=np.uint32)[0])


class _Seeded:
    """
    Shared by the named nodes in the :guilabel:`rng` block.

    A seed left unset is derived from the root seed and the node's own name, and
    written back, so the stored configuration carries the value the run used.
    """

    def resolve(self) -> int:
        """
        Settle this node's seed, deriving it from the root when it has none.

        :returns: The resolved seed.
        """
        if self.seed is None:
            root = self._config_parent._config_parent
            self.seed = _derive(root.resolve(), self.name)
            _mark_written(self, "seed")
        return self.seed

    def derive(self, key=()) -> int:
        """
        A reproducible integer to hand to something that seeds itself.

        Without a key this is the node's own seed, so a subsystem named in the
        configuration is handed the number written there. With one, a distinct value
        per key, which is how a backend seeding per object gets as many as it needs.

        :param key: What the seed is for.
        :returns: The derived seed.
        """
        seed = self.resolve()
        return _derive(seed, key) if key else seed


@config.dynamic(attr_name="strategy", required=False, default="numpy", auto_classmap=True)
class Rng(_Seeded, abc.ABC):
    """
    A named source of randomness that is drawn from.

    Kinds beyond the bundled one register themselves in this classmap through the
    ``bsb.components`` plugin group, like any other component. Whatever a kind does
    behind it, it answers with a :class:`numpy.random.Generator`, because that is what
    every component that draws expects to be handed.
    """

    name: str = config.attr(key=True)

    seed: int = config.attr(type=types.int(), required=False)
    """
    Seed for this generator. Left unset, it is derived from the root seed when the
    configuration is booted, and written back so the run can be reproduced.
    """

    @abc.abstractmethod
    def rng(self, key=()) -> np.random.Generator:  # pragma: nocover
        """
        A generator for one particular set of draws.

        ``key`` is what the draws are *for*: a chunk, a cell type, a device, a
        connection tag. Two calls with the same key give the same stream, and a key
        never includes the MPI rank, so which rank happens to do the work cannot
        change the result.

        :param key: What the draws are for.
        :returns: A seeded generator.
        """


@config.node
class NumpyRng(Rng, classmap_entry="numpy"):
    """
    Draws from :mod:`numpy`'s generators.
    """

    bit_generator: str = config.attr(type=_bit_generator, default="PCG64")
    """
    Name of the :mod:`numpy` bit generator backing the draws. Named here rather than
    left to :func:`numpy.random.default_rng`, whose choice may change between releases
    and would take every stream with it.
    """

    def rng(self, key=()) -> np.random.Generator:
        """
        A generator backed by the named bit generator.

        :param key: What the draws are for.
        :returns: A seeded generator.
        """
        sequence = np.random.SeedSequence([self.resolve(), *_stable_ints(key)])
        return np.random.Generator(_bit_generators()[self.bit_generator](sequence))


@config.dynamic(attr_name="strategy", auto_classmap=True)
class RngSettings(_Seeded):
    """
    Randomness handed *out* to a subsystem that seeds itself.

    A simulator kernel is not drawn from, and how many numbers it wants is its own
    business, so a backend registers its own kind here through the ``bsb.components``
    plugin group and reads off it what it needs.
    """

    name: str = config.attr(key=True)

    seed: int = config.attr(type=types.int(), required=False)
    """
    Seed handed to the subsystem. Left unset, it is derived from the root seed and
    written back.
    """


@config.node
class RngRootNode(NumpyRng, classmap_entry=None):
    """
    The :guilabel:`rng` block: the root seed, and the generator used by default.

    Leave :attr:`seed` unset and every run is a replicate, each output carrying the
    seed it used. Set it, or paste back the one a run recorded, and that run
    reproduces exactly. Name a generator on a component to hold one part of a model
    fixed while the rest varies.
    """

    scaffold: "Scaffold"

    name = config.unset()
    """
    A generator in :guilabel:`generators` is named by the key it is under. The block is
    reached as :guilabel:`rng` and derives from nothing, so it carries no name.
    """

    seed: int = config.attr(type=types.int(), required=False)
    """
    Root seed everything derives from, and the seed of the block's own draws. Left
    unset, one is drawn when the configuration is booted and written back, so the
    stored configuration reproduces this run.
    """

    generators: cfgdict[str, Rng] = config.dict(type=Rng)
    """
    Named sources to draw from. One with its own :guilabel:`seed` is held fixed; one
    without derives from :attr:`seed`.
    """

    settings: cfgdict[str, RngSettings] = config.dict(type=RngSettings)
    """
    Named randomness for subsystems that seed themselves, such as a simulator kernel.
    """

    def __boot__(self):
        self.resolve()
        for node in (*self.generators.values(), *self.settings.values()):
            node.resolve()
        # The block itself has to be recorded as configured, or a drawn seed would
        # resolve in memory and never reach the stored configuration.
        _mark_written(self._config_parent, "rng")

    def resolve(self) -> int:
        """
        Settle the root seed, drawing one if none was configured.

        Drawn from the operating system rather than from a fixed default, so an
        unseeded configuration is a fresh replicate every time, and written back so
        the stored configuration reproduces this run.

        :returns: The resolved root seed.
        """
        if self.seed is None:
            self.seed = int(np.random.SeedSequence().entropy % (2**32))
            _mark_written(self, "seed")
        return self.seed


class RngConsumer:
    """
    Mixin for a component that draws.

    Its :guilabel:`rng` attribute names a generator; left unset the block itself is
    the generator, so there is always one to draw from and nothing to write for the
    common case.
    """

    rng: Rng = config.ref(refs.rng_ref, required=False)
    """
    Name of the :guilabel:`generators` entry to draw from. Unset draws from the
    :guilabel:`rng` block itself.
    """

    @property
    def random_generator(self) -> Rng:
        """The generator this component draws from, named or inherited."""
        named = getattr(self, "rng", None)
        if named is not None:
            return named
        scaffold = getattr(self, "scaffold", None)
        if scaffold is None:
            raise ConfigurationError(
                f"Cannot draw randomness from {self!r}: it is not attached to a network."
            )
        return scaffold.configuration.rng

    def get_rng(self, key=()) -> np.random.Generator:
        """
        A generator for one set of draws, from whatever this component names.

        :param key: What the draws are for; see :meth:`NumpyRng.rng`.
        :returns: A seeded generator.
        """
        return self.random_generator.rng(key)


__all__ = [
    "NumpyRng",
    "RngConsumer",
    "Rng",
    "RngRootNode",
    "RngSettings",
]

__api__ = [
    "NumpyRng",
    "RngConsumer",
    "Rng",
    "RngRootNode",
    "RngSettings",
]
