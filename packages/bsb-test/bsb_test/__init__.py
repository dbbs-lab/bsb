"""
Helpers for better and more complete tests for component developers of the BSB framework.
"""

import contextlib
import glob as _glob
import os as _os
import random
import unittest
from collections import defaultdict
from importlib.metadata import EntryPoint
from pathlib import Path

import numpy as _np
import requests
from bsb import (
    Chunk,
    Configuration,
    Scaffold,
    Storage,
    UrlScheme,
    get_engine_node,
    parse_morphology_file,
)

from .configs import (
    get_test_config,
    get_test_config_tree,
    get_test_configs,
    list_test_configs,
)
from .exceptions import FixtureError
from .parallel import (
    MPI,
    internet_connection,
    on_main_only,
    serial_setup,
    skip_nointernet,
    skip_parallel,
    skip_serial,
    timeout,
)


class NetworkFixture:
    network: "Scaffold"

    def setUp(self):
        kwargs = {}
        with contextlib.suppress(Exception):
            kwargs["config"] = self.cfg
        with contextlib.suppress(Exception):
            kwargs["storage"] = self.storage
        self.network = Scaffold(**kwargs)
        super().setUp()


class RandomStorageFixture:
    storage: "Storage"

    def __init_subclass__(
        cls, root_factory=None, debug=False, setup_cls=False, *, engine_name, **kwargs
    ):
        super().__init_subclass__(**kwargs)
        cls._engine = engine_name
        cls._rootf = root_factory
        cls._open_storages = []
        cls._debug_storage = debug
        cls._setup_cls = setup_cls

    @classmethod
    def setUpClass(cls):
        if cls._setup_cls:
            cls.storage = cls.random_storage()
        super().setUpClass()

    def setUp(self):
        if not self._setup_cls:
            self.storage = self.random_storage()
        super().setUp()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        if not cls._debug_storage:
            for s in cls._open_storages:
                s.remove()

    @classmethod
    def random_storage(cls):
        if cls._rootf is not None:
            rstr = cls._rootf()
        else:
            # Get the engine's storage node default value, assuming it is random
            rstr = get_engine_node(cls._engine)(engine=cls._engine).root
        s = Storage(cls._engine, rstr)
        cls._open_storages.append(s)
        return s


class FixedPosConfigFixture:
    cfg: "Configuration"

    def setUp(self):
        self.cfg = Configuration.default(
            cell_types=dict(test_cell=dict(spatial=dict(radius=2, count=100))),
            placement=dict(
                ch4_c25=dict(
                    strategy="bsb.placement.strategy.FixedPositions",
                    partitions=[],
                    cell_types=["test_cell"],
                )
            ),
        )
        self.chunk_size = cs = self.cfg.network.chunk_size
        self.chunks = [
            Chunk((0, 0, 0), cs),
            Chunk((0, 0, 1), cs),
            Chunk((1, 0, 0), cs),
            Chunk((1, 0, 1), cs),
        ]
        self.cfg.placement.ch4_c25.positions = MPI.bcast(
            _np.vstack(
                (
                    _np.random.random((25, 3)) * cs + [0, 0, 0],
                    _np.random.random((25, 3)) * cs + [0, 0, cs[2]],
                    _np.random.random((25, 3)) * cs + [cs[0], 0, 0],
                    _np.random.random((25, 3)) * cs + [cs[0], 0, cs[2]],
                )
            )
        )
        super().setUp()


class ConfigFixture:
    def __init_subclass__(cls, config=None, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._pycfg_name = config

    def setUp(self):
        self.cfg = get_test_config(self._pycfg_name)
        super().setUp()


class MorphologiesFixture:
    def __init_subclass__(cls, morpho_filters=None, morpho_suffix="swc", **kwargs):
        super().__init_subclass__(**kwargs)
        cls._morpho_suffix = morpho_suffix
        cls._morpho_filters = morpho_filters

    def setUp(self):
        if not hasattr(self, "network"):
            raise FixtureError(
                f"{self.__class__.__name__} uses MorphologiesFixture, which requires a"
                f" network fixture."
            )
        if MPI.get_rank():
            MPI.barrier()
        else:
            for mpath in get_all_morphology_paths(self._morpho_suffix):
                if self._morpho_filters and all(
                    mpath.find(filter) == -1 for filter in self._morpho_filters
                ):
                    continue
                if mpath.endswith("swc"):
                    self.network.morphologies.save(
                        Path(mpath).stem, parse_morphology_file(mpath)
                    )
                else:
                    self.network.morphologies.save(
                        Path(mpath).stem, parse_morphology_file(mpath, parser="morphio")
                    )
            MPI.barrier()
        super().setUp()


class NumpyTestCase:
    def assertClose(self, a, b, msg="", /, **kwargs):
        if msg:
            msg += ". "
        return self.assertTrue(
            _np.allclose(a, b, **kwargs), f"{msg}Expected {a}, got {b}"
        )

    def assertNotClose(self, a, b, msg="", /, **kwargs):
        if msg:
            msg += ". "
        return self.assertFalse(
            _np.allclose(a, b, **kwargs), f"{msg}Expected {a}, got {b}"
        )

    def assertAll(self, a, msg="", /, **kwargs):
        trues = _np.sum(a.astype(bool))
        all = _np.prod(a.shape)
        if msg:
            msg += ". "
        return self.assertTrue(
            _np.all(a, **kwargs), f"{msg}Only {trues} out of {all} True"
        )

    def assertNan(self, a, msg="", /, **kwargs):
        if msg:
            msg += ". "
        nans = _np.isnan(a)
        all = _np.prod(a.shape)
        return self.assertTrue(
            _np.all(a, **kwargs), f"{msg}Only {_np.sum(nans)} out of {all} True"
        )


def get_data_path(*paths):
    return _os.path.abspath(
        _os.path.join(
            _os.path.dirname(__file__),
            "data",
            *paths,
        )
    )


def get_morphology_path(file):
    return get_data_path("morphologies", file)


def get_all_morphology_paths(suffix=""):
    yield from _glob.glob(get_data_path("morphologies", "*" + suffix))


def skipIfOffline(url=None, scheme: UrlScheme = None):
    if scheme is not None:
        err_msg = f"{type(scheme).__name__} service unavailable."
        session_ctx = scheme.create_session()
    else:
        err_msg = f"'{url}' service unavailable"
        session_ctx = requests.Session()
    try:
        url = url or scheme.get_base_url()
    except NotImplementedError as err:
        raise ValueError("Couldn't establish base URL to ping for health check.") from err
    try:
        with session_ctx as session:
            res = session.get(url)
            offline = res.status_code != 200 or "Service Interruption Notice"
    except Exception:
        offline = True
    return unittest.skipIf(offline, err_msg)


class SpoofedEntryPoint(EntryPoint):
    def __new__(cls, name, value, group, advert):
        try:
            return super().__new__(cls, name, value, group)
        except TypeError:
            return super().__new__(cls)

    def __init__(self, name, value, group, advert):
        try:
            super().__init__(name, value, group)
        except TypeError:
            super().__init__()
        self.__dict__["_advert"] = advert

    def load(self):
        return self._advert


@contextlib.contextmanager
def plugin_context(plugin_dict):
    import bsb.plugins

    eps = defaultdict(list)
    for cat, plugins in plugin_dict.items():
        for name, plugin in plugins.items():
            r = "".join(chr(random.randint(65, 90)) for _ in range(20))
            ep = SpoofedEntryPoint(name, f"__spoofed__.{cat}:{r}", cat, plugin)
            eps[cat].append(ep)
            bsb.plugins._unittest_plugins[cat].append(ep)
    yield
    for cat, plugins in eps.items():
        for plugin in plugins:
            bsb.plugins._unittest_plugins[cat].remove(plugin)


def spoof_plugin(category, name, obj):
    return spoof_plugins({category: {name: obj}})


def spoof_plugins(plugin_dict):
    def decorator(f):
        def spoofed(*args, **kwargs):
            _invalidate_plugin_caches()
            with plugin_context(plugin_dict):
                ret = f(*args, **kwargs)
            _invalidate_plugin_caches()
            return ret

        return spoofed

    return decorator


def _invalidate_plugin_caches():
    from bsb.config._make import load_component_plugins
    from bsb.simulation._backends import get_backends
    from bsb.storage._files import _get_schemes

    load_component_plugins.cache_clear()
    get_backends.cache_clear()
    _get_schemes.cache_clear()


__all__ = [
    "NetworkFixture",
    "RandomStorageFixture",
    "FixedPosConfigFixture",
    "ConfigFixture",
    "MorphologiesFixture",
    "NumpyTestCase",
    "get_data_path",
    "get_morphology_path",
    "get_all_morphology_paths",
    "skipIfOffline",
    "SpoofedEntryPoint",
    "plugin_context",
    "spoof_plugin",
    "spoof_plugins",
    "get_test_config",
    "get_test_config_tree",
    "get_test_configs",
    "list_test_configs",
    "FixtureError",
    "internet_connection",
    "skip_nointernet",
    "skip_serial",
    "skip_parallel",
    "timeout",
    "on_main_only",
    "serial_setup",
]
