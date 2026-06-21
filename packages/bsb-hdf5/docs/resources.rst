Resources
=========

The HDF5 engine exposes four concrete ``Resource`` types, one per BSB
storage interface. Each lives at a fixed path inside the file and exposes the
operations the BSB asks for. This page describes what each resource stores and
the few quirks worth knowing.

PlacementSet
------------

* Path: ``/placement/<cell_type_name>/``
* Implements: :class:`bsb.storage.interfaces.PlacementSet`
* Uses: ``ChunkLoader`` (chunked positions, rotations, morphology indices,
  labels, plus an ``additional`` ``ChunkedCollection``).

A placement set is the per-cell-type record of where cells live. Its chunked
layout (see :doc:`chunking`) lets workers append disjoint chunks in parallel
without contending on a single growing dataset.

Notable methods:

* ``load_morphologies`` returns a ``MorphologySet`` keyed on the
  ``morphology_loaders`` attribute the placement step wrote per chunk. It opens
  one handle which the nested ``_get_morphology_loaders`` (itself decorated)
  reuses automatically through the ambient-handle ContextVar. See
  :doc:`handles`.
* ``append_data`` accepts ``positions``, ``morphologies``, ``rotations``,
  ``additional`` for a chunk, calls ``require_chunk`` to materialise the
  chunk group on first write, then appends to each chunked property in turn.
  The per-chunk ``morphology_loaders`` attribute is rewritten on every append
  by ``_append_morphologies``.
* ``convert_to_local`` maps a list of global cell ids into local-chunk
  indices for the loaded chunk filter. Use when the caller only has the
  flat-array indices but needs to write back to specific chunk groups.

ConnectivitySet
---------------

* Path: ``/connectivity/<tag>/``
* Implements: :class:`bsb.storage.interfaces.ConnectivitySet`

A connectivity set is the per-tag record of synapses between one presynaptic
and one postsynaptic cell type. Underneath, it stores per-source-chunk and
per-destination-chunk groups so the BSB can answer "all connections out of
chunk X" or "all connections into chunk Y" without reading the whole set.

Notable methods:

* ``flat_iter_connections`` iterates over per-chunk connection blocks.
* ``connect`` writes a new block of (src_locs, dst_locs) pairs into the
  appropriate chunk groups and updates the root ``chunks`` JSON attribute's
  ``inc`` / ``out`` counters.

The ``ConnectivitySet.__init__`` is decorated with
``@handles_handles("r", handler=lambda args: args[1])`` because at
construction time ``self._engine`` does not exist yet; the handler picks the
engine off the second positional argument instead.

MorphologyRepository
--------------------

* Path: ``/morphologies/``
* Implements: :class:`bsb.storage.interfaces.MorphologyRepository`

The morphology repository stores reusable morphology trees. Each morphology
gets a group at ``/morphologies/<name>/`` containing a ``data`` dataset (one
row per point: ``[x, y, z, radius, label, *properties]``) and a ``graph``
dataset (one row per branch: ``[end_ptr, parent_branch_id]``).

A single ``morphology_meta`` dataset at ``/`` holds the JSON-encoded metadata
for every morphology in the file. Reading it via ``get_all_meta`` is the
one cheap operation that lets the placement step decide which morphology to
load without touching any morphology group.

Notable methods:

* ``preload`` builds a ``StoredMorphology`` from a name + meta dict.
  Pass ``meta=`` in to skip the meta lookup (the common path when iterating
  over many morphologies). Called from inside an open handle (an enclosing scope
  or decorated method) it reuses that handle automatically; see :doc:`handles`.
* ``save`` writes a ``Morphology`` to disk and updates the
  ``morphology_meta`` attribute.

FileStore
---------

* Path: ``/files/``
* Implements: :class:`bsb.storage.interfaces.FileStore`

The file store holds arbitrary blobs by id (uuid4-by-default). Each blob is a
single dataset under ``/files/<id>`` with two attributes:

* ``meta`` (JSON dict, includes at minimum ``mtime``)
* ``encoding`` (optional, e.g. ``utf-8`` if the blob originated as a string)

The file store is also where the **active config** lives: a special blob
flagged with ``meta["active_config"] = True``, retrievable via
``load_active_config``. Only one blob carries that flag at a time;
``store_active_config`` clears it on the previous holder before flagging
the new one.

Unlike the other resources, the file store does not use the
``handles_handles`` decorator: every method opens its own handle in the
body via ``with self._engine._read(), self._engine._handle("r")``. This is
intentional: the file store is mostly called as a one-shot from user code, not
from inside other engine paths, so threading would not pay off.

.. _batching-reads-writes:

Batching reads and writes
-------------------------

Methods that loop over many morphologies, files, or chunks and dispatch to
nested resource calls benefit most from handle reuse. Nested decorated calls
inherit an open handle automatically (via the ambient-handle ContextVar), and a
caller that drives many *top-level* reads or writes can hold a single handle for
the whole batch with :meth:`~bsb_hdf5.HDF5Engine.read_scope` /
:meth:`~bsb_hdf5.HDF5Engine.write_scope` (or the engine-agnostic
``storage.read_scope()`` / ``storage.write_scope()``).

See :doc:`handles` for the full discipline, including the
:class:`~bsb_hdf5.resource.PromotedHandleWarning` and
:class:`~bsb_hdf5.resource.UnusedWriteScopeWarning` the engine raises when a
scope is misused.
