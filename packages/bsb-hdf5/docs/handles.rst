Handles
=======

Every read or write inside the engine goes through ``h5py.File``, and every
``h5py.File`` open sits behind the ``MPILock``. Opening the file is the
most expensive operation an engine method can do. This page explains the
discipline that keeps it cheap: open one handle, then reuse it for as long as
possible.

The ``handles_handles`` decorator
---------------------------------

Any method on a ``Resource`` that needs an HDF5 handle is decorated and
takes a ``handle`` keyword argument:

.. code-block:: python

   @handles_handles("r")
   def load_morphologies(self, handle=HANDLED):
       ...

On each call the decorator resolves a handle in this order:

1. **Explicit handle.** If the caller passed a non-None ``handle=``, the body
   runs with that handle. No lock, no open.
2. **Ambient handle.** Otherwise it checks the per-engine handle
   :class:`~contextvars.ContextVar`, set by an enclosing
   :meth:`~bsb_hdf5.HDF5Engine.read_scope` / :meth:`~bsb_hdf5.HDF5Engine.write_scope`
   block or by any outer ``@handles_handles`` call that already opened one. If a
   compatible handle is open it is reused. (A write handle satisfies both read
   and write requests; a read handle satisfies only reads.)
3. **Fresh handle.** Otherwise it acquires the matching mpilock (``r`` -> read
   lock, ``a`` -> write lock), opens the file, registers the handle on the
   ContextVar so nested decorated calls inherit it, runs the body, then tears
   down.

Step 2 is the whole performance story: nested decorated calls reuse the open
handle automatically, with no manual plumbing.

Automatic reuse, and the explicit override
-------------------------------------------

Because step 3 registers the handle on the ContextVar, a decorated method that
calls other decorated methods on the same engine shares its handle with them
for free:

.. code-block:: python

   @handles_handles("r")
   def load_morphologies(self, handle=HANDLED):
       # `_get_morphology_loaders` is itself @handles_handles("r"); it finds the
       # ambient handle on the ContextVar and reuses it. No lock, no open.
       loaders = self._get_morphology_loaders()
       ...

Passing ``handle=handle`` explicitly still works and takes precedence over the
ambient lookup. Use it when you hold a handle that is not on the ContextVar
(for example one received as an argument), or to be explicit at a hot call site.
A non-decorated helper that needs to take part in reuse (for example a mixin
like ``ChunkLoader.get_loaded_chunks``) accepts a ``handle=`` keyword and
passes it on to the decorated calls it makes.

The ContextVar propagates across threads and asyncio tasks that go through
:func:`contextvars.copy_context`, including the path the BSB job pool takes
(``Job.run`` uses ``ctx.run`` on the worker thread). It does *not*
propagate across MPI ranks: each rank has its own handle and its own lock.

Batching with ``read_scope`` and ``write_scope``
------------------------------------------------

The ambient lookup only helps once a handle is open. To batch many *top-level*
decorated calls behind a single lock + open, wrap them in a scope:

.. code-block:: python

   with engine.read_scope():
       for chunk in chunks:
           ps.load_positions()       # every call reuses one handle
           cs.get_chunk_stats()

   with engine.write_scope():
       for chunk, data in batch:
           ps.append_data(chunk, data)

:meth:`~bsb_hdf5.HDF5Engine.read_scope` opens one read handle and holds it for
the block; :meth:`~bsb_hdf5.HDF5Engine.write_scope` opens one write handle.
Every decorated call inside reuses it. :class:`~bsb.storage.Storage` exposes the
same two methods, which delegate to the engine, so callers above the engine
layer use ``storage.read_scope()`` without holding an engine reference.

Without a scope, a loop of N top-level reads pays N lock acquires and N file
opens. Inside a read scope it pays one of each.

``PromotedHandleWarning``
-------------------------

A write operation (``@handles_handles("a")``) called inside a **read** scope is
legal: mpilock promotes the held read lock to a write for that one call, then
returns to the read state. The promotion is safe but briefly serializes every
reader and writer across the cluster, so it is usually a refactor target (move
the write outside the read scope). The engine emits
:class:`~bsb_hdf5.resource.PromotedHandleWarning` to flag it. If the write is
genuinely small, one-off, and cannot be moved, pass ``promote_from_read=True``
at the call site to silence the warning.

``UnusedWriteScopeWarning``
---------------------------

A :meth:`~bsb_hdf5.HDF5Engine.write_scope` block that exits without any
``@handles_handles("a")`` operation running inside held the cluster-wide write
lock for nothing, blocking other writers. The engine emits
:class:`~bsb_hdf5.resource.UnusedWriteScopeWarning` on exit. The fix is to use
:meth:`~bsb_hdf5.HDF5Engine.read_scope` if the block only reads, or to drop the
scope and let individual decorated calls open their own short-lived handles.

The cost of not batching
------------------------

Each redundant open costs:

* one MPI-collective lock acquire (microseconds in isolation, much more under
  reader contention from other ranks),
* one ``h5py.File()`` construction (slow on Lustre and other network
  filesystems),
* one ``hdf5.file.open`` OTel span if the SDK is active.

On a typical HPC run, an unbatched loop that visits N morphologies turns into
~N * 200 ms of pure overhead, with no signal in the work itself, and the cost
grows with cluster size because every other rank's lock acquires queue behind
ours.
