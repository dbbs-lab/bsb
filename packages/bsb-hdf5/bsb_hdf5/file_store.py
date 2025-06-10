import contextlib
import json
import time
from uuid import uuid4

import numpy as np
from bsb import FileStore as IFileStore
from bsb import MissingActiveConfigError

from .resource import Resource

_root = "files"


class FileStore(Resource, IFileStore):
    def __init__(self, engine):
        super().__init__(engine, _root)

    def __bool__(self):
        return True

    def all(self):
        with self._engine._read(), self._engine._handle("r") as root:
            store = root[self._path]
            return {id: json.loads(f.attrs.get("meta", "{}")) for id, f in store.items()}

    def load(self, id):
        with self._engine._read(), self._engine._handle("r") as root:
            ds = root[f"{self._path}/{id}"]
            data = ds[()]
            if encoding := ds.attrs.get("encoding", None):
                data = data.decode(encoding)
            return data, json.loads(ds.attrs.get("meta", "{}"))

    def remove(self, id):
        with self._engine._write(), self._engine._handle("a") as root:
            del root[f"{self._path}/{id}"]

    def store(self, content, meta=None, id=None, encoding=None, overwrite=False):
        if id is None:
            id = str(uuid4())
        if meta is None:
            meta = {}
        meta["mtime"] = int(time.time())
        with self._engine._write(), self._engine._handle("a") as root:
            store = root[self._path]
            if isinstance(content, str):
                if encoding is None:
                    encoding = "utf-8"
                content = content.encode(encoding)
            content = np.array(content)
            if overwrite:
                with contextlib.suppress(KeyError):
                    del store[id]
            try:
                ds = store.create_dataset(id, data=content)
            except ValueError:
                raise Exception(f"File `{id}` already exists in store.") from None
            if encoding:
                ds.attrs["encoding"] = encoding
            ds.attrs["meta"] = json.dumps(meta)
            ds.attrs["mtime"] = meta["mtime"]
        return id

    def load_active_config(self):
        """
        Load the active configuration stored inside the storage.

        :returns: The active configuration that is loaded when this storage object is.
        :rtype: ~bsb.config.Configuration
        """
        from bsb.config import Configuration

        cfg_id = self._active_config_id()
        if cfg_id is None:
            raise MissingActiveConfigError("No active config")
        else:
            content, meta = self.load(cfg_id)
            # It's a serialized Python dict, so it should be JSON readable. We don't use
            # evaluate because files might originate from untrusted sources.
            tree = json.loads(content)
            cfg = Configuration(**tree)
            cfg._meta = meta
            return cfg

    def store_active_config(self, config):
        """
        Set the active configuration for this network.

        :param config: The active configuration that will be loaded when this storage
            object is.
        :type config: ~bsb.config.Configuration
        """
        id = self._active_config_id()
        self._engine.comm.barrier()
        if id is not None and self._engine.comm.get_rank() == 0:
            self.remove(id)
        config._meta["active_config"] = True
        active_id = None
        if self._engine.comm.get_rank() == 0:
            meta = {k: v for k, v in config._meta.items() if v is not None}
            active_id = self.store(json.dumps(config.__tree__()), meta)
        return self._engine.comm.bcast(active_id, root=0)

    def _active_config_id(self):
        match = (id for id, m in self.all().items() if m.get("active_config", False))
        return next(match, None)

    def has(self, id):
        with self._engine._read(), self._engine._handle("r") as root:
            return id in root

    def get_mtime(self, id):
        with self._engine._read(), self._engine._handle("r") as root:
            return root[self._path][id].attrs["mtime"]

    def get_encoding(self, id):
        with self._engine._read(), self._engine._handle("r") as root:
            return root[self._path][id].attrs.get("encoding", None)

    def get_meta(self, id):
        with self._engine._read(), self._engine._handle("r") as root:
            return json.loads(root[self._path][id].attrs.get("meta", "{}"))
