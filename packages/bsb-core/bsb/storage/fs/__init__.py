import contextlib
import importlib.metadata
import json
import os
import shutil
import tempfile
import warnings
from datetime import datetime
from pathlib import Path

import shortuuid

from ... import config
from ...exceptions import BsbProvenanceUpgradeWarning
from ...services import MPILock
from ..decorators import on_main_until
from ..interfaces import Engine, NoopLock
from ..interfaces import StorageNode as IStorageNode
from ..provenance import build_root_metadata
from .file_store import FileStore  # noqa: F401

_METADATA_FILENAME = "metadata.json"
_LEGACY_VERSIONS_FILENAME = "versions.txt"


def _metadata_path(root: str) -> Path:
    return Path(root) / _METADATA_FILENAME


def _legacy_versions_path(root: str) -> Path:
    return Path(root) / _LEGACY_VERSIONS_FILENAME


def _atomic_write_json(path: Path, payload: dict) -> None:
    """Write JSON to ``path`` via a tmp file + os.replace so readers never see partials."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(payload, f, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(Exception):
            os.unlink(tmp)
        raise


class FileSystemEngine(Engine):
    def __init__(self, root, comm):
        super().__init__(root, comm)
        self._lock = MPILock.sync()
        self._readonly = False
        self._upgrade_if_needed()

    @property
    def root_slug(self):
        return os.path.relpath(self._root)

    @property
    def versions(self):
        md = self.metadata
        if md:
            return {
                "bsb": md.get("bsb_core_version"),
                "engine": "fs",
                "version": md.get("engine_version") or md.get("bsb_core_version"),
            }
        # Pre-upgrade legacy fallback.
        legacy = _legacy_versions_path(self._root)
        if legacy.exists():
            return json.loads(legacy.read_text())
        return {}

    @property
    def metadata(self) -> dict:
        path = _metadata_path(self._root)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            return {}

    def _bump_state(self) -> None:
        if self._readonly:
            return
        # Serialise the read-modify-write through the engine lock so concurrent
        # ranks can't clobber each other's metadata.json.
        with self._write():
            md = self.metadata
            if not md:
                return
            md["state_id"] = int(md.get("state_id", 0)) + 1
            _atomic_write_json(_metadata_path(self._root), md)

    def _upgrade_if_needed(self):
        if self._readonly or not self.exists():
            return
        if _metadata_path(self._root).exists():
            return
        with self._write():
            # Re-check under the lock: another rank may have upgraded already,
            # so only the first rank in writes the bundle and warns.
            if _metadata_path(self._root).exists():
                return
            bundle = build_root_metadata(
                engine_name="fs",
                engine_version=importlib.metadata.version("bsb-core"),
                mpi_size=self.comm.get_size(),
            )
            bundle["state_id"] = 1
            _atomic_write_json(_metadata_path(self._root), bundle)
            legacy = _legacy_versions_path(self._root)
            if legacy.exists():
                try:
                    legacy.unlink()
                except OSError:
                    pass
            warnings.warn(
                "Auto-upgraded legacy FS storage with a fresh storage_id and "
                "provenance bundle.",
                category=BsbProvenanceUpgradeWarning,
                stacklevel=3,
            )

    @staticmethod
    def recognizes(root, comm):
        try:
            return os.path.exists(root) and os.path.isdir(root)
        except Exception:
            return False

    def _read(self):
        if self._readonly:
            return NoopLock()
        else:
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

    def exists(self):
        return os.path.exists(self._root)

    @on_main_until(lambda self: self.exists())
    def create(self):
        os.makedirs(os.path.join(self._root, "files"), exist_ok=True)
        os.makedirs(os.path.join(self._root, "file_meta"), exist_ok=True)
        bundle = build_root_metadata(
            engine_name="fs",
            engine_version=importlib.metadata.version("bsb-core"),
            mpi_size=self.comm.get_size(),
        )
        _atomic_write_json(_metadata_path(self._root), bundle)

    @on_main_until(lambda self: self.exists())
    def move(self, new_root):
        shutil.move(self._root, new_root)
        self._root = new_root

    @on_main_until(lambda self, r: self.__class__(self.root, self.comm).exists())
    def copy(self, new_root):
        shutil.copytree(self._root, new_root)

    @on_main_until(lambda self: not self.exists())
    def remove(self):
        shutil.rmtree(self._root)

    def require_placement_set(self, ct):
        raise NotImplementedError("No PS")

    def clear_placement(self):
        pass

    def clear_connectivity(self):
        pass

    def get_chunk_stats(self):
        return {}


def _get_default_root():
    return os.path.abspath(
        os.path.join(
            ".",
            "scaffold_network_"
            + datetime.now().strftime("%Y_%m_%d")
            + "_"
            + shortuuid.uuid(),
        )
    )


@config.node
class StorageNode(IStorageNode):
    root = config.attr(type=str, default=_get_default_root, call_default=True)
    """
    Path to the filesystem storage file.
    """
