import datetime
import importlib.metadata
import json
import os
import sys
import typing
import warnings
from pathlib import Path
from traceback import format_exception

import appdirs

from glia._hash import hash_installs, hash_path

_install_dirs = appdirs.AppDirs(appname="Glia", appauthor="DBBS")

LogLevel = typing.Literal["log"] | typing.Literal["warn"] | typing.Literal["error"]


def log(message: str, *, level: LogLevel = None, category=None, exc: Exception = None):
    log_path = Path(get_cache_path(f"{id('5')}.txt"))
    if exc is not None and level is None:
        level = "error"
    if level:
        level = level.upper()
    header = " ".join(str(c) for c in (datetime.datetime.now(), level, category) if c)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a") as f:
        f.write(f"[{header}] {message}")
        if exc:
            f.write(":\n")
            f.writelines(
                "  " + "\n  ".join(line.split("\n"))
                for line in format_exception(type(exc), exc, exc.__traceback__)
            )
            f.write("Exception arguments:\n")
            f.writelines(f"  {a}\n" for a in exc.args)
            warnings.warn(message + f". See the full log at '{log_path}'.", stacklevel=2)
        else:
            f.write("\n")


def get_glia_path():
    from . import __path__

    return __path__[0]


def get_cache_hash(prefix=""):
    return (
        prefix
        + hash_path(get_glia_path())[:8]
        + hash_path(sys.prefix)[:8]
        + hash_installs()
    )


def get_cache_path(*subfolders, prefix=""):
    return os.path.join(
        _install_dirs.user_cache_dir,
        get_cache_hash(prefix),
        *subfolders,
    )


def get_data_path(*subfolders):
    return os.path.join(_install_dirs.user_data_dir, *subfolders)


def get_neuron_mod_path(*paths):
    return get_cache_path(*paths)


def get_local_pkg_path():
    return get_data_path(importlib.metadata.version("nmodl-glia").split(".")[0], "local")


def _read_shared_storage(*path):
    _path = get_data_path(*path)
    try:
        with open(_path) as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _write_shared_storage(data, *path):
    _path = get_data_path(*path)
    with open(_path, "w") as f:
        f.write(json.dumps(data))


def read_storage(*path):
    data = _read_shared_storage(*path)
    glia_path = get_glia_path()
    if glia_path not in data:
        return {}
    return data[glia_path]


def write_storage(data, *path):
    _path = get_data_path(*path)
    glia_path = get_glia_path()
    shared_data = _read_shared_storage(*path)
    shared_data[glia_path] = data
    _write_shared_storage(shared_data, *path)


def read_cache():
    cache = read_storage("cache.json")
    if "mod_hashes" not in cache:
        cache["mod_hashes"] = {}
    return cache


def write_cache(cache_data):
    write_storage(cache_data, "cache.json")


def update_cache(cache_data):
    cache = read_cache()
    cache.update(cache_data)
    write_cache(cache)


def clear_cache():
    empty_cache = {"mod_hashes": {}, "cat_hashes": {}}
    write_cache(empty_cache)


def read_preferences():
    return read_storage("preferences.json")


def write_preferences(preferences):
    write_storage(preferences, "preferences.json")


def create_preferences():
    write_storage({}, "preferences.json")
