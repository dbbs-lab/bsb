import itertools
import json

import numpy as np
from bsb import (
    Chunk,
    DatasetExistsError,
    DatasetNotFoundError,
    MissingMorphologyError,
    MorphologySelector,
    MorphologySet,
    RotationSet,
    config,
)
from bsb import PlacementSet as IPlacementSet
from bsb._encoding import EncodedLabels

from .chunks import ChunkedCollection, ChunkedProperty, ChunkLoader
from .resource import (
    HANDLED,
    Resource,
    handles_class_handles,
    handles_handles,
    handles_static_handles,
)

_root = "/placement/"


@config.node
class _MapSelector(MorphologySelector):
    ps = config.attr(type=lambda x: x)
    names = config.attr(type=lambda x: x)

    def __init__(self, *, ps=None, names=None):
        self._ps = ps
        self._names = set(names)

    def validate(self, loaders):
        missing = set(self._names) - {m.get_meta()["name"] for m in loaders}
        if missing:
            raise MissingMorphologyError(
                "Morphology repository misses the following morphologies required by"
                + f" {self._ps.tag}: {', '.join(missing)}"
            )

    def pick(self, stored_morphology):
        name = stored_morphology.get_meta()["name"]
        return name in self._names


_ps_properties = (
    lambda loader: ChunkedProperty(loader, "position", shape=(0, 3), dtype=float),
    lambda loader: ChunkedProperty(loader, "rotation", shape=(0, 3), dtype=float),
    lambda loader: ChunkedProperty(loader, "morphology", shape=(0,), dtype=int),
    lambda loader: ChunkedProperty(
        loader, "labels", shape=(0,), dtype=int, extract=encode_labels
    ),
)
_ps_collections = (
    lambda loader: ChunkedCollection(loader, "additional", shape=None, dtype=float),
)


class PlacementSet(
    Resource,
    ChunkLoader,
    IPlacementSet,
    properties=_ps_properties,
    collections=_ps_collections,
):
    """
    Fetches placement data from storage.

    .. note::

        Use :meth:`Scaffold.get_placement_set <bsb.core.Scaffold.get_placement_set>` to
        correctly obtain a PlacementSet.
    """

    _position_chunks: ChunkedProperty
    _morphology_chunks: ChunkedProperty
    _rotation_chunks: ChunkedProperty
    _labels_chunks: ChunkedProperty
    _additional_chunks: ChunkedCollection

    def __init__(self, engine, cell_type):
        tag = cell_type.name
        Resource.__init__(self, engine, _root + tag)
        IPlacementSet.__init__(self, engine, cell_type)
        ChunkLoader.__init__(self)
        self._labels = None
        self._morphology_labels = None
        if not self.exists(engine, cell_type):
            raise DatasetNotFoundError(f"PlacementSet '{tag}' does not exist")

    @classmethod
    @handles_class_handles("a")
    def create(cls, engine, cell_type, handle=HANDLED):
        """
        Create the structure for this placement set in the HDF5 file.

        Placement sets are
        stored under ``/placement/<tag>``.
        """
        tag = cell_type.name
        path = _root + tag
        if path in handle:
            raise DatasetExistsError(f"PlacementSet '{tag}' already exists.")
        handle.create_group(path)
        return cls(engine, cell_type)

    @staticmethod
    @handles_static_handles("r")
    def exists(engine, cell_type, handle=HANDLED):
        return "/placement/" + cell_type.name in handle

    @classmethod
    @handles_class_handles("a")
    def require(cls, engine, cell_type, handle=HANDLED):
        tag = cell_type.name
        path = _root + tag
        handle.require_group(path)
        return cls(engine, cell_type)

    @handles_handles("r")
    def load_positions(self, handle=HANDLED):
        """
        Load the cell positions.

        :raises: DatasetNotFoundError when there is no rotation information for this cell
            type.
        """
        try:
            positions = self._position_chunks.load(handle=handle)
        except DatasetNotFoundError:
            raise DatasetNotFoundError(
                f"No position information for the '{self.tag}' placement set."
            ) from None
        else:
            if self._labels:
                mask = self.get_label_mask(self._labels, handle=handle)
                return positions[mask]
            else:
                return positions

    @handles_handles("r")
    def load_rotations(self, handle=HANDLED):
        """
        Load the cell rotations.

        :raises: DatasetNotFoundError when there is no rotation information for this cell
            type.
        """
        data = self._rotation_chunks.load(handle=handle)
        if len(data) == 0 and len(self) != 0:
            raise DatasetNotFoundError("No rotation data available.")
        if self._labels:
            mask = self.get_label_mask(self._labels, handle=handle)
            data = data[mask]
        return RotationSet(data)

    @handles_handles("r")
    def load_morphologies(self, handle=HANDLED, allow_empty=False):
        """
        Preload the cell morphologies.

        :param handle: hdf5 file handler
        :type handle: :class:`h5py.File`
        :param allow_empty: If False (default), will raise an error in absence of
         morphologies,
        :type allow_empty: bool
        :returns: MorphologySet object containing the loader of all morphologies
        :rtype: bsb.morphologies.MorphologySet
        :raises: DatasetNotFoundError when the morphology data is not found.
        """
        reader = self._morphology_chunks.get_chunk_reader(handle, True)
        loaders = self._get_morphology_loaders(handle=handle)
        data = []
        if loaders:
            for chunk in self.get_loaded_chunks():
                path = self.get_chunk_path(chunk)
                try:
                    _map = handle[path].attrs["morphology_loaders"]
                except KeyError:
                    continue
                block = np.vectorize(list(loaders.keys()).index)(_map[reader(chunk)])
                if len(block):
                    data.append(block)
        if len(data) == 0 and (len(self) != 0 or len(loaders) == 0):
            if not allow_empty:
                raise DatasetNotFoundError("No morphology data available.")
            else:
                data = np.empty(0, dtype=int)
        else:
            data = np.concatenate(data)
        if self._labels:
            mask = self.get_label_mask(self._labels, handle=handle)
            data = data[mask]
        return MorphologySet(
            list(loaders.values()),
            data,
            labels=self._morphology_labels,
        )

    @handles_handles("r")
    def load_additional(self, key=None, handle=HANDLED):
        if key is None:
            return self._additional_chunks.load_all()
        else:
            return self._additional_chunks.load(key)

    @handles_handles("r")
    def _get_morphology_loaders(self, handle=HANDLED):
        stor_mor = {}
        meta = self._engine.morphologies.get_all_meta()
        for chunk in self.get_loaded_chunks():
            path = self.get_chunk_path(chunk)
            try:
                _map = handle[path].attrs["morphology_loaders"]
            except KeyError:
                continue
            for label in _map:
                if label not in stor_mor:
                    if label in meta:
                        stor_mor[label] = self._engine.morphologies.preload(
                            name=label, meta=meta[label]
                        )
                    else:
                        raise DatasetNotFoundError(
                            f"No metadata found for stored morphology {label}"
                        )
        return stor_mor

    @handles_handles("a")
    def _set_morphology_loaders(self, map, handle=HANDLED):
        for chunk in self.get_loaded_chunks():
            path = self.get_chunk_path(chunk)
            handle[path].attrs["morphology_loaders"] = map

    def __iter__(self):
        return itertools.zip_longest(
            self.load_positions(),
            self.load_morphologies(),
        )

    def __len__(self):
        if self._labels:
            return np.sum(self._labels_chunks.load().get_mask(self._labels))
        else:
            return len(self._position_chunks.load())

    @handles_handles("a")
    def append_data(
        self,
        chunk,
        positions=None,
        morphologies=None,
        rotations=None,
        additional=None,
        count=None,
        handle=HANDLED,
    ):
        """
        Append data to the placement set.

        :param chunk: The chunk to store data in.
        :type chunk: ~bsb.storage._chunks.Chunk
        :param positions: Cell positions
        :type positions: :class:`numpy.ndarray`
        :param rotations: Cell rotations
        :type rotations: ~bsb.morphologies.RotationSet
        :param morphologies: Cell morphologies
        :type morphologies: ~bsb.morphologies.MorphologySet
        :param additional: Additional data to attach to chunk
        :type additional: dict
        :param count: Amount of entities to place. Excludes the use of any positional,
          rotational or morphological data.
        :type count: int
        :param handle: hdf5 file handler
        :type handle: :class:`h5py.Group`
        """
        if not isinstance(chunk, Chunk):
            chunk = Chunk(chunk, None)
        if positions is not None:
            positions = np.array(positions, copy=False)
        if count is not None:
            if not (positions is None and morphologies is None):
                raise ValueError(
                    "The `count` keyword is reserved for creating entities,"
                    + " without any positional, or morphological data."
                )
            self.require_chunk(chunk, handle=handle)

        if positions is not None:
            self._position_chunks.append(chunk, positions)
        if morphologies is not None:
            self._append_morphologies(chunk, morphologies)
            if rotations is None:
                rotations = np.zeros((len(morphologies), 3))
        if rotations is not None:
            self._rotation_chunks.append(chunk, rotations)

        if additional is not None:
            for key, ds in additional.items():
                self.append_additional(key, chunk, ds)
        self._track_add(handle, chunk, len(positions) if positions is not None else count)

    def _append_morphologies(self, chunk, new_set):
        with self.chunk_context([chunk]):
            morphology_set = self.load_morphologies(allow_empty=True).merge(new_set)
            self._set_morphology_loaders(morphology_set._serialize_loaders())
            self._morphology_chunks.clear(chunk)
            self._morphology_chunks.append(chunk, morphology_set.get_indices())

    def append_entities(self, chunk, count, additional=None):
        """
        Append entities to the placement set.

        :param chunk: The chunk to store data in.
        :type chunk: ~bsb.storage._chunks.Chunk
        :param count: Amount of entities to place. Excludes the use of any positional,
            rotational or morphological data.
        :type count: int
        :param additional: Additional data to attach to chunk
        :type additional: dict
        """
        self.append_data(chunk, count=count, additional=additional)

    def append_additional(self, name, chunk, data):
        self._additional_chunks.append(chunk, name, data)

    @handles_handles("a")
    def clear(self, chunks=None, handle=HANDLED):
        path = _root + self.tag
        g = handle.require_group(path)
        stats = self._engine._read_chunk_stats(handle)
        for chunk, data in g.items():
            if chunks is None or chunk in chunks:
                stats[chunk]["placed"] -= len(data["position"])
                del g[chunk]
        self._engine._write_chunk_stats(handle, stats)

    @handles_handles("a")
    def label_by_mask(self, mask, labels, handle=HANDLED):
        cells = np.array(mask, copy=False)
        if cells.dtype != bool or len(cells) != len(self):
            raise LabellingException("Mask doesn't fit data.")
        self._write_labels(
            labels,
            handle,
            lambda: self._lendemux(),
            lambda s: cells[s],
        )

    @handles_handles("a")
    def label(self, labels, cells, handle=HANDLED):
        cells = np.array(cells, copy=False)
        len_ = len(self)
        oob = cells > len_
        if np.any(oob):
            oob_idx = cells[oob]
            raise LabellingException(
                f"Cell labels {oob_idx} out of range for placement set with size {len_}."
            )
        self._write_labels(
            labels,
            handle,
            lambda: self._demux(cells),
            lambda x: x,
        )

    def _write_labels(self, labels, handle, demux_f, data_f):
        # Create a label reader that can read out label data per chunk, and pads missing
        # cells with unlabelled cells.
        label_reader = self._labels_chunks.get_chunk_reader(
            handle, False, pad_by="position"
        )
        updated_labels = None
        # Demultiplex the cells per chunk. demux_f sets chunk context to current chunk
        for chunk, block in demux_f():
            enc_labels = label_reader(chunk)
            # The label reader gets the labelsets from a shared attribute on the PS, so we
            # keep and update 1 shared reference, that we update after the loop.
            if updated_labels:
                enc_labels.labels = updated_labels
            else:
                updated_labels = enc_labels.labels
            # Label the cells
            enc_labels.label(labels, data_f(block))
            # Overwrite with new labelled data.
            self._labels_chunks.overwrite(chunk, enc_labels, handle=handle)
        # Update the shared labelset reference on the PS.
        if updated_labels is not None:
            handle[self._path].attrs["labelsets"] = json.dumps(
                updated_labels, default=list
            )

    def set_label_filter(self, labels):
        self._labels = labels

    def set_morphology_label_filter(self, morphology_labels):
        """
        Sets the labels by which any morphology loaded from this set will be filtered.

        :param morphology_labels: List of labels to filter the morphologies by.
        :type morphology_labels: List[str]
        """
        self._morphology_labels = morphology_labels

    @handles_handles("r")
    def get_unique_labels(self, handle=HANDLED):
        u, c = np.unique(
            self._labels_chunks.load(handle=handle, pad_by="position"),
            return_counts=True,
        )
        # take out the extra empty set
        return list(u.labels.values())[-len(c) :]

    @handles_handles("r")
    def get_labelled(self, labels=None, handle=HANDLED):
        mask = self.get_label_mask(labels, handle=handle)
        return np.nonzero(mask)[0]

    @handles_handles("r")
    def get_label_mask(self, labels=None, handle=HANDLED):
        return self._labels_chunks.load(handle=handle, pad_by="position").get_mask(labels)

    def _lendemux(self):
        """
        .. warning::

            This function sets the chunk context for as long as it iterates.
        """
        ctr = 0
        for chunk in self.get_loaded_chunks():
            with self.chunk_context([chunk]):
                len_ = len(self)
                yield chunk, slice(ctr, ctr := ctr + len_)

    def _demux(self, ids):
        """
        .. warning::

            This function sets the chunk context for as long as it iterates.
        """
        for chunk in self.get_loaded_chunks():
            with self.chunk_context([chunk]):
                ln = len(self)
                idx = ids < ln
                block = ids[idx]
                yield chunk, block
                ids = ids[~idx]
                ids -= ln

    def _track_add(self, handle, chunk, count):
        # Track addition in global chunk stats
        global_stats = json.loads(handle.attrs.get("chunks", "{}"))
        stats = global_stats.setdefault(
            str(chunk.id), {"placed": 0, "connections": {"inc": 0, "out": 0}}
        )
        stats["placed"] += int(count)
        handle.attrs["chunks"] = json.dumps(global_stats)
        # Track addition in placement set
        handle[self._path].attrs["len"] = handle[self._path].attrs.get("len", 0) + count
        chunk_stats = json.loads(handle[self._path].attrs.get("chunks", "{}"))
        chunk_stats[str(chunk.id)] = chunk_stats.get(str(chunk.id), 0) + int(count)
        handle[self._path].attrs["chunks"] = json.dumps(chunk_stats)

    @handles_handles("r")
    def get_chunk_stats(self, handle=HANDLED):
        return json.loads(handle[self._path].attrs["chunks"])

    @handles_handles("r")
    def load_ids(self, handle=HANDLED):
        if self._chunks is None or not len(self._chunks):
            return np.arange(len(self))
        stats = self.get_chunk_stats(handle)
        ranges = []
        ctr = 0
        for chunk, len_ in sorted(
            stats.items(), key=lambda k: Chunk.from_id(int(k[0]), None).id
        ):
            if chunk in self._chunks:
                ranges.append(np.arange(ctr, ctr + len_))
            ctr += len_
        return np.concatenate(ranges)

    @handles_handles("r")
    def convert_to_local(self, ids, handle=HANDLED):
        """
        Converts a list of global ids to local ids, if the PlacementSet is not separated
        in chunks check the ids within a range on the full size of the PS.
        """

        if self._chunks is None or not len(self._chunks):
            return ids
        chunks = [x.id for x in self._chunks]
        stats = np.array([[int(k), v] for k, v in self.get_chunk_stats(handle).items()])
        ids = np.array(ids)
        ordered_stats_indexes = np.argsort(stats[:, 0])
        ordered_stats = stats[ordered_stats_indexes]
        cumulative_chunk_lengths = np.cumsum(ordered_stats[:, 1])

        # Get list of Chunk id for every number in ids -> chunk_id_of_glob
        chunk_id_of_glob = np.searchsorted(cumulative_chunk_lengths - 1, ids)

        # Now i will need to select only local chunks
        local_chunk_filter = np.isin(ordered_stats[:, 0], chunks)
        common_elements = np.arange(len(ordered_stats))[local_chunk_filter]
        local_chunks_stats = (
            ordered_stats[:, 1] * local_chunk_filter
        )  # Extract stats only for local chunks (ordered)

        # Compute a list of offset for local chunks
        local_cumulative_lenghts = np.cumsum(local_chunks_stats)

        # From ids list we filter out only the elements that do not belong to local chunks
        filter_ids_of_local_chunks = np.isin(chunk_id_of_glob, common_elements)
        filtered_ids = ids[filter_ids_of_local_chunks]
        filtered_chunk_id = chunk_id_of_glob[
            filter_ids_of_local_chunks
        ]  # filter also the list of Chunk id

        # Compute converted ids  by taking
        # the GlobalId - OffsetonGlobalChunks + OffsetOnLocalChunks
        converted_ids = np.zeros(len(filtered_ids), dtype=int)

        for i, my_id in enumerate(filtered_ids):
            converted_ids[i] = (
                my_id
                - cumulative_chunk_lengths[filtered_chunk_id[i]]
                + local_cumulative_lenghts[filtered_chunk_id[i]]
            )
        return (
            converted_ids
            if len(converted_ids) > 0
            else np.full(np.sum(local_chunks_stats), False)
        )


def encode_labels(data, ds):
    if ds is None:
        return EncodedLabels.none(len(data))
    ps_group = ds.parent.parent
    serialized = json.dumps(EncodedLabels.none(1).labels, default=list)
    labels = json.loads(ps_group.attrs.get("labelsets", serialized))
    return EncodedLabels(shape=data.shape, buffer=data, labels=labels)


class LabellingException(Exception):
    pass
