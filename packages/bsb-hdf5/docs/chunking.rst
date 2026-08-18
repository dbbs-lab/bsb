Chunked storage
===============

The placement and connectivity data the BSB produces is naturally chunked: a
chunk is a fixed-size axis-aligned region of space, identified by an integer
ID. Workers process one chunk at a time, and the engine stores each chunk's
data under its own HDF5 group so workers can append without contending on the
same dataset.

This page describes how that chunking lands in the file and how to use the
``ChunkLoader`` mixin to read it back.

The chunk size attribute
------------------------

The root of the file carries a ``chunk_size`` attribute, set the first time any
resource writes a chunk. Every subsequent write must match it (mismatch raises).
This is the source of truth for the spatial size of every chunk in the file.

Chunks at rest
--------------

A ``ChunkLoader`` lives at ``self._path``. Each chunk it owns gets a group
at ``self._path/<chunk.id>``. Inside that group:

* One **dataset** per ``ChunkedProperty``, named after the property
  (``positions``, ``rotations``, ``morphology``, ``labels`` for a PlacementSet).
* One **group** per ``ChunkedCollection``, named after the collection
  (``additional`` for a PlacementSet). The collection group holds one dataset
  per arbitrary key stored under it.

Example for ``/placement/granule_cell``:

::

   /placement/granule_cell/
   ├── 12345/                 (chunk id 12345)
   │   ├── positions          (N, 3) float
   │   ├── rotations          (N, 3) float
   │   ├── morphology         (N,) int
   │   ├── labels             (N,) int
   │   └── additional/        (group)
   │       └── ...
   ├── 12346/
   │   └── ...
   └── attrs:
       ├── len                (total cells across all chunks)
       └── chunks             (JSON: per-chunk-id count)

The ``ChunkLoader`` mixin
-------------------------

A resource that wants chunked storage inherits from ``ChunkLoader`` and
declares its properties / collections in the subclass parameters:

.. code-block:: python

   class PlacementSet(
       Resource,
       ChunkLoader,
       IPlacementSet,
       properties=(
           lambda loader: ChunkedProperty(loader, "position", shape=(0, 3), dtype=float),
           lambda loader: ChunkedProperty(loader, "rotation", shape=(0, 3), dtype=float),
           ...
       ),
       collections=(
           lambda loader: ChunkedCollection(loader, "additional", shape=None, dtype=float),
       ),
   ):
       ...

The mixin gives the subclass:

* ``get_loaded_chunks`` returns the chunks currently in the load filter, or
  every chunk in the file if no filter is set. Accepts ``handle=`` so a
  decorated caller can pass its handle on to this non-decorated helper. See
  :doc:`handles`.
* ``get_all_chunks`` reads the keys of ``self._path`` and returns the full
  chunk list. Decorated with ``@handles_handles("r")`` so it opens its own
  handle if not given one.
* ``get_chunk_path`` returns the full HDF5 path of a chunk's group, or a
  property/collection dataset inside it.
* ``require_chunk`` creates the chunk group + property datasets on first
  write. Decorated with ``@handles_handles("a")``.
* ``include_chunk``, ``exclude_chunk``, ``set_chunk_filter``,
  ``clear_chunk_filter`` manage the in-memory load filter.
* ``chunk_context`` is a context manager that temporarily replaces the
  load filter for the duration of a block.

The chunk-id ordering matters
-----------------------------

``ChunkedProperty.load`` concatenates chunks in the order they appear in
``get_loaded_chunks``. The order must be stable between writers and
readers; chunk lists are produced via :func:`bsb.storage._chunks.chunklist`
which sorts on the integer chunk id.

If you bypass the chunk loader and read raw chunk groups directly, you must
sort the same way before concatenating, or downstream consumers (``load_ids``,
``load_positions``, label masks) will desync.

Stats and the global ``chunks`` attribute
-----------------------------------------

The file root carries a JSON ``chunks`` attribute mapping chunk id to placement
and connection counts:

.. code-block:: json

   {
     "12345": {"placed": 1024, "connections": {"inc": 0, "out": 0}},
     "12346": {"placed":  512, "connections": {"inc": 0, "out": 0}}
   }

This is maintained by ``PlacementSet._track_add`` (on append) and the
connectivity-write paths. It lets the BSB report counts and decide
work-distribution without having to walk every chunk group.
