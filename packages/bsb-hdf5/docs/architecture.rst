Architecture
============

The HDF5 engine is one engine implementation of the BSB storage interface. It
backs a network with a single HDF5 file on shared storage, accessed concurrently
by every MPI rank. The engine's job is to make that work safely and fast.

The pieces
----------

.. list-table::
   :widths: 25 75

   * - :class:`HDF5Engine`
     - Engine entry point. Owns the file path, the :class:`MPILock`, and the
       ``_handle`` factory that opens the file. Provides the rank-collective
       ``create``, ``move``, ``copy``, ``remove``, ``clear_placement``,
       ``clear_connectivity`` operations via the ``on_main`` /
       ``on_main_until`` decorators.
   * - :class:`Resource` (resource.py)
     - Base class for everything that lives at a path inside the HDF5 file. The
       :func:`handles_handles` decorator does the open-on-entry, close-on-exit,
       lock-while-open dance.
   * - :class:`ChunkLoader` (chunks.py)
     - Mixin that gives a resource per-chunk read/write of its
       :class:`ChunkedProperty` and :class:`ChunkedCollection` datasets.
   * - :class:`PlacementSet`, :class:`ConnectivitySet`, :class:`MorphologyRepository`, :class:`FileStore`
     - The four resource implementations the BSB asks for.
   * - :mod:`bsb_hdf5._telemetry`
     - The local-only ``_hdf5_tracer`` used by every span the engine emits.

File layout
-----------

After :meth:`HDF5Engine.create`, the file has four top-level groups:

::

   /
   ├── placement/        # one group per cell type, plus chunk-indexed datasets
   ├── connectivity/     # one group per connectivity set
   ├── files/            # the file store (blob + meta pairs)
   ├── morphologies/     # one group per morphology, plus the morphology_meta dataset
   └── attrs:
       ├── bsb_version
       ├── bsb_hdf5_version
       ├── chunk_size       (set on first placement, read by all subsequent reads)
       └── chunks           (JSON: per-chunk placement and connectivity counts)

Sub-layouts are documented per resource in :doc:`resources`.

The MPI lock
------------

Every HDF5 read or write goes through :class:`bsb.services.MPILock`, an MPI
RMA-based reader/writer lock:

* Multiple :meth:`_read` holders can hold the read lock simultaneously.
* :meth:`_write` is exclusive against both other writers and any readers.
* :meth:`_master_write` is single-writer rank-0-only and skips the
  reader-counting handshake.

The engine acquires the right kind of lock via the :func:`handles_handles`
decorator. The lock is held for the full body of the decorated function (i.e.,
for as long as the HDF5 handle is open). Every additional ``handle=None`` call
inside that body re-acquires the lock and re-opens the file. See :doc:`handles`
for why this matters.

The handle wrapper
------------------

:class:`_SpannedHandle` wraps the real :class:`h5py.File` so that every open
emits an ``hdf5.file.open`` OTel span covering its lifetime, with
``hdf5.file.slow_lock`` flagged if the OS-level h5py lock had to back off and
retry. The retry loop in :meth:`HDF5Engine._handle` caps at 10 000 attempts
(~10 s) before aborting; emitting a :class:`HDF5SlowLockingWarning` when any
retry happened.

The rank-collective decorators
------------------------------

A handful of engine operations must run on rank 0 only and have their result
broadcast to the rest of the ranks:

* ``@on_main()`` runs the wrapped function on rank 0, broadcasts the return.
* ``@on_main_until(condition)`` runs on rank 0, then *all* ranks busy-wait on
  ``condition(self, ...)`` until it holds. Use this for file lifecycle
  operations where the cohort must observe the side effect (e.g. ``create``,
  ``move``, ``remove``) before continuing.

These are the only methods that intentionally diverge between ranks. Everything
else is symmetric: every rank executes it; the lock and h5py serialise.

Telemetry
---------

The engine instruments every decorated entry point and every file open with an
OTel span. See :doc:`telemetry` for the architecture of the engine-local
tracer wrapper (and why it forces ``local_tracing`` around hdf5 spans).
