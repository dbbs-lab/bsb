import unittest

import numpy as np
from bsb_test import RandomStorageFixture

from bsb import CastError, CfgReferenceError, NumpyRng, Scaffold
from bsb.config import Configuration


class _NetworkMixin:
    """Builds networks whose only interesting configuration is their randomness."""

    def network(self, rng=None):
        kwargs = {}
        if rng is not None:
            kwargs["rng"] = rng
        return Scaffold(Configuration.default(**kwargs), self.random_storage())


class TestReplicateAndReproduce(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """The two modes the whole design exists to provide."""

    def draw(self, network):
        return network.configuration.rng.rng(key=("place", (0, 0, 0), "cell")).random()

    def test_an_unseeded_config_is_a_new_replicate_every_run(self):
        seeds = {self.network().configuration.rng.seed for _ in range(3)}
        self.assertEqual(3, len(seeds), "an unseeded run must not repeat itself")

    def test_every_run_records_the_seed_it_used(self):
        network = self.network()
        stored = network.configuration.__tree__()["rng"]
        self.assertEqual(
            network.configuration.rng.seed,
            stored["seed"],
            "a drawn seed must reach the stored configuration, or the run is lost",
        )

    def test_feeding_a_recorded_config_back_reproduces_the_run(self):
        first = self.network()
        recorded = first.configuration.__tree__()["rng"]

        self.assertEqual(self.draw(first), self.draw(self.network(recorded)))

    def test_a_pinned_seed_is_left_alone(self):
        network = self.network({"seed": 1234})
        self.assertEqual(1234, network.configuration.rng.seed)
        self.assertEqual(1234, network.configuration.__tree__()["rng"]["seed"])


class TestTheBlockIsTheDefaultGenerator(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """
    The block is a generator itself, so there is always one to draw from.

    Nothing is auto-created and no name is reserved: a configuration that says nothing
    but a seed still has a generator, and it is the block.
    """

    def test_the_block_draws_without_declaring_anything(self):
        rng = self.network({"seed": 42}).configuration.rng
        self.assertIsInstance(rng.rng(key=("x",)), np.random.Generator)

    def test_nothing_is_added_to_a_bare_block(self):
        stored = self.network({"seed": 42}).configuration.__tree__()["rng"]
        self.assertNotIn(
            "generators", stored, "a bare block must not grow entries nobody wrote"
        )

    def test_the_bit_generator_is_named_not_inherited_from_numpy(self):
        # `default_rng` may change which bit generator it returns between releases,
        # which would move every stream with it.
        rng = self.network({"seed": 42}).configuration.rng
        self.assertEqual("PCG64", rng.bit_generator)
        self.assertEqual(
            "PCG64", type(rng.rng(key=("x",)).bit_generator).__name__, "not honoured"
        )

    def test_a_name_that_is_not_a_bit_generator_is_caught(self):
        # `numpy.random` carries plenty of names that are not bit generators, and a
        # typo reads the same in a configuration file. Both have to fail here rather
        # than at the first draw somewhere else entirely.
        for name in ("PCG46", "Generator", "SeedSequence", "seed"):
            with self.subTest(bit_generator=name), self.assertRaises(CastError):
                self.network({"seed": 42, "bit_generator": name})

    def test_another_bit_generator_gives_another_stream(self):
        same_seed = {"seed": 42, "bit_generator": "Philox"}
        other = self.network(same_seed).configuration.rng
        self.assertNotEqual(
            self.network({"seed": 42}).configuration.rng.rng(key=("x",)).random(),
            other.rng(key=("x",)).random(),
        )


class TestDerivation(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """Streams are derived from what is being drawn for, never from the rank."""

    def setUp(self):
        super().setUp()
        self.rng = self.network({"seed": 42}).configuration.rng

    def test_the_same_key_gives_the_same_stream(self):
        self.assertEqual(
            self.rng.rng(key=("place", (0, 0, 0))).random(),
            self.rng.rng(key=("place", (0, 0, 0))).random(),
        )

    def test_different_keys_give_different_streams(self):
        draws = {
            self.rng.rng(key=key).random()
            for key in (
                ("place", (0, 0, 0), "cell_a"),
                ("place", (1, 0, 0), "cell_a"),
                ("place", (0, 0, 0), "cell_b"),
                ("connect", (0, 0, 0), "cell_a"),
            )
        }
        self.assertEqual(4, len(draws), "each thing drawn for gets its own stream")

    def test_a_string_key_is_stable_across_processes(self):
        # Python's own `hash` is salted per process; a salted key would reseed on
        # every invocation and silently destroy reproducibility.
        import subprocess
        import sys

        script = (
            "from bsb.rng import _stable_ints; print(_stable_ints(('place', 'cell_a')))"
        )
        runs = {
            subprocess.run(
                [sys.executable, "-c", script], capture_output=True, text=True
            ).stdout.strip()
            for _ in range(2)
        }
        self.assertEqual(1, len(runs), f"key hashing is not stable: {runs}")

    def test_generators_derive_from_the_root_seed(self):
        rng = self.network({"seed": 7, "generators": {"structure": {}}}).configuration.rng
        generator = rng.generators["structure"]
        self.assertIsNotNone(generator.seed, "an unpinned generator derives a seed")
        self.assertNotEqual(7, generator.seed, "and it is not just the root seed")

    def test_a_pinned_generator_holds_while_the_rest_varies(self):
        # The workflow this exists for: same network, different simulation noise.
        pinned = {"generators": {"structure": {"seed": 99}}}
        first, second = self.network(pinned), self.network(pinned)

        self.assertEqual(
            first.configuration.rng.generators["structure"].rng(("chunk",)).random(),
            second.configuration.rng.generators["structure"].rng(("chunk",)).random(),
            "a pinned generator must not move between runs",
        )
        self.assertNotEqual(
            first.configuration.rng.seed,
            second.configuration.rng.seed,
            "while the root seed still varies",
        )


class TestHandingSeedsOut(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """
    A subsystem that seeds itself is handed numbers, not a generator.

    Arity is the subsystem's business: one kernel seed, or one per object, comes from
    calling `derive` once or once per key.
    """

    def test_a_pinned_setting_is_handed_the_number_that_was_written(self):
        rng = self.network(
            {"seed": 1, "generators": {"kernel": {"seed": 999}}}
        ).configuration.rng
        self.assertEqual(
            999,
            rng.generators["kernel"].derive(),
            "a seed written in the configuration is the seed handed out",
        )

    def test_a_key_gives_a_distinct_number_per_object(self):
        rng = self.network(
            {"seed": 1, "generators": {"kernel": {"seed": 999}}}
        ).configuration.rng
        node = rng.generators["kernel"]
        per_gid = {node.derive(("poisson", gid)) for gid in range(50)}
        self.assertEqual(50, len(per_gid), "each object gets its own seed")
        self.assertNotIn(999, per_gid, "and none of them is the node's own seed")


class TestWhatAComponentDrawsFrom(
    RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """
    A component names its generator, or says nothing and draws from the block.

    A reference is only consulted when there is a name to resolve, so what an unset
    one falls back to is the component's own business, not the reference's.
    """

    def net(self, rng, strat_rng=None):
        placement = {
            "strategy": "bsb.placement.RandomPlacement",
            "cell_types": ["test_cell"],
            "partitions": ["test_part"],
        }
        if strat_rng is not None:
            placement["rng"] = strat_rng
        return Scaffold(
            Configuration.default(
                rng=rng,
                cell_types={"test_cell": {"spatial": {"radius": 1, "count": 4}}},
                partitions={"test_part": {"thickness": 10}},
                placement={"p": placement},
            ),
            self.storage,
        )

    def test_saying_nothing_draws_from_the_block(self):
        net = self.net({"seed": 42})
        strategy = net.placement.p
        self.assertIsNone(strategy.rng, "nothing was named")
        self.assertIs(strategy.random_generator, net.configuration.rng)
        self.assertEqual(
            strategy.get_rng(key=("x",)).random(),
            net.configuration.rng.rng(key=("x",)).random(),
            "and it draws the stream the block would give",
        )

    def test_a_named_generator_is_the_one_drawn_from(self):
        net = self.net(
            {"seed": 42, "generators": {"structure": {"seed": 7}}}, "structure"
        )
        strategy = net.placement.p
        self.assertIs(strategy.rng, net.configuration.rng.generators["structure"])
        self.assertNotEqual(
            strategy.get_rng(key=("x",)).random(),
            net.configuration.rng.rng(key=("x",)).random(),
            "a named generator is not the block",
        )

    def test_a_name_that_does_not_exist_is_caught(self):
        # The point of a reference over a string: an unknown name stops the boot
        # rather than quietly drawing a different stream.
        with self.assertRaises(CfgReferenceError):
            self.net({"seed": 42}, "nope")


class TestAKindThatIsNotNumpy(
    _NetworkMixin, RandomStorageFixture, unittest.TestCase, engine_name="hdf5"
):
    """
    `generators` is not a numpy-only block.

    What a kind does behind `rng` is its own business; the block's contract is that a
    component is handed something it can draw from.
    """

    def setUp(self):
        super().setUp()
        from bsb import config
        from bsb.rng import Rng

        @config.node
        class OneNumberRng(Rng, classmap_entry="one_number"):
            """Hands back a generator that was seeded by hand, not by a bit generator."""

            def rng(self, key=()):
                return np.random.Generator(np.random.MT19937(self.resolve()))

        self.addCleanup(Rng._config_dynamic_classmap.pop, "one_number", None)

    def test_a_registered_kind_is_named_and_drawn_from(self):
        net = self.network(
            {"seed": 1, "generators": {"custom": {"strategy": "one_number"}}}
        )
        generator = net.configuration.rng.generators["custom"]
        self.assertNotIsInstance(generator, NumpyRng, "the block took a kind of its own")
        self.assertIsInstance(
            generator.rng(key=("x",)),
            np.random.Generator,
            "and it still answers with something to draw from",
        )


class TestKeyEncoding(unittest.TestCase):
    """
    Keys that mean different things must not share a stream.

    A seed sequence absorbs a trailing zero and rejects a negative outright, so the
    encoding cannot hand it either.
    """

    def stream(self, key):
        from bsb.rng import _stable_ints

        seq = np.random.SeedSequence([1234, *_stable_ints(key)])
        return tuple(seq.generate_state(4).tolist())

    def test_keys_that_differ_give_different_streams(self):
        for name, one, other in [
            ("None is not the integer 0", ("a", None), ("a", 0)),
            ("a trailing None is not absent", ("a",), ("a", None)),
            ("a trailing 0 is not absent", ("a",), ("a", 0)),
            ("False is not the integer 0", ("a", False), ("a", 0)),
            ("True is not the integer 1", ("a", True), ("a", 1)),
            ("nesting is part of the key", ("a", (1, 2)), ("a", 1, 2)),
            ("order is part of the key", (1, 2), (2, 1)),
        ]:
            with self.subTest(case=name):
                self.assertNotEqual(self.stream(one), self.stream(other), name)

    def test_a_negative_element_is_a_key_like_any_other(self):
        for key in [("chunk", -1), ("chunk", np.array([-3, 0, 7])), ("chunk", -(2**40))]:
            with self.subTest(key=str(key)):
                self.assertEqual(self.stream(key), self.stream(key), "not stable")
        self.assertNotEqual(
            self.stream(("chunk", -1)),
            self.stream(("chunk", 1)),
            "sign is part of the key",
        )
