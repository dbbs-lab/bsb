"""
HDF5 storage engine for the BSB framework.
"""

import importlib.metadata
import json
import os
import shutil
from datetime import datetime

import h5py
import shortuuid
from bsb import Engine, MPILock, config, report
from bsb import StorageNode as IStorageNode

from .connectivity_set import ConnectivitySet
from .file_store import FileStore
from .morphology_repository import MorphologyRepository
from .placement_set import PlacementSet

__all__ = [
    "PlacementSet",
    "ConnectivitySet",
    "FileStore",
    "MorphologyRepository",
    "HDF5Engine",
    "StorageNode",
]


def on_main(prep=None, ret=None):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            r = None
            self.comm.barrier()
            if self.comm.get_rank() == 0:
                r = f(self, *args, **kwargs)
            elif prep:
                prep(self, *args, **kwargs)
            self.comm.barrier()
            if not ret:
                return self.comm.bcast(r, root=0)
            else:
                return ret(self, *args, **kwargs)

        return wrapper

    return decorator


def on_main_until(until, prep=None, ret=None):
    def decorator(f):
        def wrapper(self, *args, **kwargs):
            global _procpass
            r = None
            self.comm.barrier()
            if self.comm.get_rank() == 0:
                r = f(self, *args, **kwargs)
            elif prep:
                prep(self, *args, **kwargs)
            self.comm.barrier()
            while not until(self, *args, **kwargs):
                pass
            if not ret:
                return self.comm.bcast(r, root=0)
            else:
                return ret(self, *args, **kwargs)

        return wrapper

    return decorator


def _set_root(self, root):
    self._root = root


def _set_active_cfg(self, config):
    config._meta["active_config"] = True


class NoopLock:
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class HDF5Engine(Engine):
    def __init__(self, root, comm):
        super().__init__(root, comm)
        self._lock = MPILock.sync(comm._comm)
        self._readonly = False

    @on_main()
    @property
    def versions(self):
        with self._handle("r") as handle:
            return {
                "bsb": handle.attrs["bsb_version"],
                "engine": "bsb-hdf5",
                "version": handle.attrs["bsb_hdf5_version"],
            }

    @property
    def root_slug(self):
        return os.path.relpath(self._root)

    @staticmethod
    def recognizes(root, comm):
        lock = MPILock.sync(comm)
        with lock.read():
            try:
                h5py.File(root, "r").close()
                return True
            except Exception as e:
                report(f"Cannot open hdf5 file {root}: {e}.", level=1)
                return False

    def _read(self):
        # h5py does not deal with concurrent read access
        return self._lock.read()

    def _write(self):
        if self._readonly:
            raise OSError("Can't perform write operations in readonly mode.")
        else:
            return self._lock.write()

    def _master_write(self):
        if self._readonly:
            raise OSError("Can't perform write operations in readonly mode.")
        else:
            return self._lock.single_write()

    def _handle(self, mode):
        if self._readonly and mode != "r":
            raise OSError("Can't perform write operations in readonly mode.")
        else:
            return h5py.File(self._root, mode)

    def exists(self):
        return os.path.exists(self._root)

    @on_main_until(lambda self: self.exists())
    def create(self):
        with self._handle("w") as handle:
            handle.attrs["bsb_hdf5_version"] = importlib.metadata.version("bsb-hdf5")
            handle.attrs["bsb_version"] = importlib.metadata.version("bsb-core")
            handle.create_group("placement")
            handle.create_group("connectivity")
            handle.create_group("files")
            handle.create_group("morphologies")

    @on_main_until(lambda self, r: self.exists(), _set_root)
    def move(self, new_root):
        shutil.move(self._root, new_root)
        self._root = new_root

    @on_main_until(lambda self, r: self.__class__(self.root, self.comm).exists())
    def copy(self, new_root):
        shutil.copy(self._root, new_root)

    @on_main_until(lambda self: not self.exists())
    def remove(self):
        os.remove(self._root)

    @on_main_until(
        lambda self, ct: PlacementSet.exists(self, ct),
        prep=None,
        ret=lambda self, ct: PlacementSet(self, ct),
    )
    def require_placement_set(self, ct):
        return PlacementSet.require(self, ct)

    @on_main()
    def clear_placement(self):
        with self._handle("a") as handle:
            handle.require_group("placement")
            del handle["placement"]
            del handle.attrs["chunk_size"]
            handle.require_group("placement")
            self._write_chunk_stats(handle, {})

    @on_main()
    def clear_connectivity(self):
        with self._handle("a") as handle:
            handle.require_group("connectivity")
            del handle["connectivity"]
            handle.require_group("connectivity")
            stats = self._read_chunk_stats(handle)
            stats = {
                k: {"placed": v["placed"], "connections": {"inc": 0, "out": 0}}
                for k, v in stats.items()
            }
            self._write_chunk_stats(handle, stats)

    @on_main()
    def get_chunk_stats(self):
        with self._handle("r") as handle:
            return self._read_chunk_stats(handle)

    def _read_chunk_stats(self, handle: h5py.File) -> object:
        return json.loads(handle.attrs.get("chunks", "{}"))

    def _write_chunk_stats(self, handle, stats):
        handle.attrs["chunks"] = json.dumps(stats)


def _get_default_root():
    return os.path.abspath(
        os.path.join(
            ".",
            "scaffold_network_"
            + datetime.now().strftime("%Y_%m_%d")
            + "_"
            + shortuuid.uuid()
            + ".hdf5",
        )
    )


@config.node
class StorageNode(IStorageNode):
    root = config.attr(type=str, default=_get_default_root, call_default=True)
    """
    Path to the HDF5 network storage file.
    """
