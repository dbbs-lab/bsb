"""
The chunks module provides the tools for the HDF5 engine to store the chunked placement
data received from the placement module in separate datasets to arbitrarily parallelize
and scale scaffold models.

The module provides the :class:`.ChunkLoader` mixin for
:class:`~.resource.Resource` objects (e.g. PlacementSet,
ConnectivitySet) to organize :class:`.ChunkedProperty` and :class:`.ChunkedCollection`
objects within them.
"""

import contextlib

import numpy as np
from bsb import Chunk, chunklist

from .resource import HANDLED, handles_handles


class ChunkLoader:
    """
    :class:`~.resource.Resource` mixin to organize chunked properties and collections
    within itself.

    :param properties: An iterable of functions that construct :class:`.ChunkedProperty`.
    :type: Iterable
    :param collections: An iterable of names for constructing :class:`.ChunkedCollection`.
    :type: Iterable
    """

    def __init_subclass__(cls, properties=(), collections=(), **kwargs):
        super().__init_subclass__(**kwargs)
        cls._properties = list(properties)
        cls._collections = list(collections)

    def __init__(self):
        self._chunks = []
        self._properties = []
        self._collections = []
        for prop_constr in self.__class__._properties:
            prop = prop_constr(self)
            self.__dict__[f"_{prop.name}_chunks"] = prop
            self._properties.append(prop)
        for prop_constr in self.__class__._collections:
            prop = prop_constr(self)
            self.__dict__[f"_{prop.collection}_chunks"] = prop
            self._collections.append(prop)

    def get_loaded_chunks(self):
        if not self._chunks:
            return self.get_all_chunks()
        else:
            return self._chunks.copy()

    @handles_handles("r")
    def get_all_chunks(self, handle=HANDLED):
        chunks = list(handle[self._path].keys())
        size = None
        if chunks:
            # If any chunks have been written, this HDF5 file is tagged with a
            # chunk size
            size = self._get_chunk_size(handle)

        return chunklist(Chunk.from_id(int(c), size) for c in chunks)

    @contextlib.contextmanager
    def chunk_context(self, chunks):
        old_chunks = self._chunks
        self._chunks = chunklist(chunks)
        yield
        self._chunks = old_chunks

    def get_chunk_path(self, chunk=None, collection=None, key=None):
        """
        Return the full HDF5 path of a chunk.

        :param chunk: Chunk
        :type chunk: :class:`bsb.storage._chunks.Chunk`
        :returns: HDF5 path
        :rtype: str
        """
        path = f"{self._path}"
        if chunk is not None:
            path += f"/{chunk.id}"
            if collection is not None:
                path += f"/{collection}"
            if key is not None:
                path += f"/{key}"
        return path

    def include_chunk(self, chunk):
        """
        Include a chunk in the data when loading properties/collections.
        """
        self._chunks.append(chunk if isinstance(chunk, Chunk) else Chunk(chunk, None))
        self._chunks.sort()

    def exclude_chunk(self, chunk):
        """
        Exclude a chunk from the data when loading properties/collections.
        """
        self._chunks.remove(chunk if isinstance(chunk, Chunk) else Chunk(chunk, None))

    def set_chunk_filter(self, chunks):
        self._chunks = chunklist(chunks)

    def clear_chunk_filter(self):
        self._chunks = []

    @handles_handles("a")
    def require_chunk(self, chunk, handle=HANDLED):
        """
        Create a chunk if it doesn't exist yet, or do nothing.
        """
        path = self.get_chunk_path(chunk)
        if path not in handle:
            chunk_group = handle.create_group(path)
            self._set_chunk_size(handle, chunk.dimensions)
            for p in self._properties:
                chunk_group.create_dataset(
                    f"{path}/{p.name}", p.shape, maxshape=p.maxshape, dtype=p.dtype
                )
            for c in self._collections:
                chunk_group.create_group(path + f"/{c.collection}")

    def _set_chunk_size(self, handle, size):
        fsize = handle.attrs.get("chunk_size", np.full(3, np.nan))
        if np.all(np.isnan(fsize)):
            handle.attrs["chunk_size"] = size
        elif not np.all(np.isnan(size)) and not np.allclose(fsize, size):
            raise Exception(f"Chunk size mismatch. File: {fsize}. Given: {size}")

    def _get_chunk_size(self, handle):
        return handle.attrs["chunk_size"]


# The ChunkedProperty and ChunkedCollection are a bit fucked in terms of inheritance and
# how they handle their polymorphism...
class ChunkedProperty:
    """
    Chunked properties are stored inside the ``chunks`` group of the :class:`.ChunkLoader`
    they belong to.

    Inside the ``chunks`` group another group is created per chunk, inside which a
    dataset exists per property.
    """

    def __init__(
        self, loader, property, shape, dtype, insert=None, extract=None, collection=None
    ):
        self.loader = loader
        self.name = property
        self.collection = collection
        self.dtype = dtype
        self.shape = shape
        self.insert = insert
        self.extract = extract
        if shape is not None:
            maxshape = list(shape)
            maxshape[0] = None
            self.maxshape = tuple(maxshape)
        else:
            self.maxshape = None

    @handles_handles("r", lambda args: args[0].loader._engine)
    def load(self, raw=False, key=None, pad_by=None, handle=HANDLED):
        chunks = self.loader.get_loaded_chunks()
        reader = self.get_chunk_reader(handle, raw, key, pad_by=pad_by)
        # Read and collect all non empty chunks
        chunked_data = tuple(data for c in chunks if (data := reader(c)).size)
        # No data? Return empty
        if not chunked_data:
            data = np.empty(self.shape if self.shape is not None else 0)
            if self.extract and not raw:
                return self.extract(data, None)
            else:
                return data
        # Allow custom ndarrays with concatenate methods to concatenate themselves.
        if concatenator := getattr(chunked_data[0].__class__, "concatenate", None):
            return concatenator(*chunked_data)
        else:
            return np.concatenate(chunked_data)

    def get_chunk_reader(self, handle, raw, key=None, pad_by=None):
        """
        Create a chunk reader that either returns the raw data or extracts it.
        """
        key = self.name if key is None else key

        def read_chunk(chunk, pad=0):
            pad_shape = self.shape[1:] if self.shape is not None else ()
            if pad_by:
                pad = len(handle[self._chunk_path(chunk, pad_by)])
            try:
                chunk_group = handle[self._chunk_path(chunk, key)]
            except KeyError:
                chunk_group = None
                data = np.zeros((pad, *pad_shape), dtype=self.dtype)
            else:
                data = chunk_group[()]
                if len(data) < pad:
                    fillshape = (pad - len(data), *pad_shape)
                    data = np.concatenate((data, np.zeros(fillshape, dtype=self.dtype)))
            if not (raw or self.extract is None):
                data = self.extract(data, chunk_group)
            return data

        # Return the created function
        return read_chunk

    @handles_handles("a", lambda args: args[0].loader._engine)
    def append(self, chunk, data, key=None, handle=HANDLED):
        """
        Append data to a property chunk. Will create it if it doesn't exist.

        :param data: Data to append to the chunked property.
        :param chunk: Chunk
        :type chunk: :class:`bsb.storage._chunks.Chunk`
        """
        key = key or self.name
        if self.insert is not None:
            data = self.insert(data)
        self.loader.require_chunk(chunk, handle)
        chunk_group = handle[self._chunk_path(chunk)]
        if key not in chunk_group:
            if self.shape is None:
                shape = data.shape
                maxshape = list(shape)
                maxshape[0] = None
            else:
                shape = list(self.shape)
                shape[0] = len(data)
                maxshape = self.maxshape
            chunk_group.create_dataset(
                key,
                shape,
                data=data,
                maxshape=maxshape,
                dtype=self.dtype,
            )
        else:
            dset = chunk_group[key]
            start_pos = dset.shape[0]
            dset.resize(start_pos + len(data), axis=0)
            dset[start_pos:] = data

    @handles_handles("a", lambda args: args[0].loader._engine)
    def clear(self, chunk, key=None, handle=HANDLED):
        key = key or self.name
        chunk_group = handle[self._chunk_path(chunk)]
        if key not in chunk_group:
            chunk_group.create_dataset(
                key,
                self.shape,
                data=np.empty(self.shape, dtype=self.dtype),
                maxshape=self.maxshape,
                dtype=self.dtype,
            )
        else:
            dset = chunk_group[key]
            dset.resize(0, axis=0)

    @handles_handles("a", lambda args: args[0].loader._engine)
    def overwrite(self, chunk, data, key=None, handle=HANDLED):
        self.clear(chunk, key, handle)
        self.append(chunk, data, key, handle)

    def _chunk_path(self, chunk, key=None):
        return self.loader.get_chunk_path(chunk, self.collection, key)


class ChunkedCollection(ChunkedProperty):
    """
    Chunked collections are stored inside the ``chunks`` group of the
    :class:`.ChunkLoader` they belong to.

    Inside the ``chunks`` group another group is created per chunk, inside which a group
    exists per collection. Arbitrarily named datasets can be stored inside of this
    collection.
    """

    def __init__(self, loader, collection, shape, dtype, insert=None, extract=None):
        super().__init__(loader, None, shape, dtype, insert, extract, collection)

    @handles_handles("r", lambda args: args[0].loader._engine)
    def keys(self, handle=HANDLED):
        try:
            return list(handle[self.loader._path].attrs[f"{self.collection}_keys"])
        except KeyError:
            return []

    @handles_handles("r", lambda args: args[0].loader._engine)
    def load(self, key, handle=HANDLED, **kwargs):
        return super().load(key=key, handle=handle, **kwargs)

    @handles_handles("a", lambda args: args[0].loader._engine)
    def append(self, chunk, key, data, handle=HANDLED, **kwargs):
        self._add_key(key, handle=handle)
        return super().append(chunk, data, key=key, handle=handle, **kwargs)

    @handles_handles("a", lambda args: args[0].loader._engine)
    def overwrite(self, chunk, data, key, handle=HANDLED, **kwargs):
        self._add_key(key, handle=handle)
        return super().overwrite(chunk, data, key=key, handle=handle, **kwargs)

    @handles_handles("a", lambda args: args[0].loader._engine)
    def clear(self, chunk, handle=HANDLED):
        del handle[self._chunk_path(chunk)]
        handle.create_group(self._chunk_path(chunk))

    @handles_handles("a", lambda args: args[0].loader._engine)
    def _add_key(self, key, handle=HANDLED):
        keys = set(self.keys(handle=handle))
        keys.add(key)
        handle[self.loader._path].attrs[f"{self.collection}_keys"] = list(keys)

    @handles_handles("r", lambda args: args[0].loader._engine)
    def load_all(self, handle=HANDLED, **kwargs):
        print("?", self)
        return {
            key: super(type(self), self).load(key=key, handle=handle, **kwargs)
            for key in self.keys()
        }
