Telemetry
=========

Every method decorated with ``handles_handles`` emits an OTel span named
``hdf5.<method_name>``. Every file open emits an ``hdf5.file.open`` span
(carrying ``hdf5.file.slow_lock`` and ``hdf5.file.wait_ms`` when the OS-level
h5py lock had to retry). Every MPI lock acquire emits an ``mpilock.*`` span
through :mod:`bsb.services.mpilock`.

This page documents the engine-local tracer wrapper and explains why the
engine forces ``local_tracing`` around every span it emits.

The local tracer
----------------

The engine does *not* call ``get_bsb_tracer`` directly. It
goes through ``_LocalHdf5Tracer``:

.. code-block:: python

   from bsb_otel.tracer import get_bsb_tracer, local_tracing

   _inner = get_bsb_tracer("bsb-hdf5")


   class _LocalHdf5Tracer:
       @staticmethod
       @contextlib.contextmanager
       def trace(name, attributes=None):
           with (
               local_tracing(),
               _inner.trace(name, attributes=attributes) as span,
           ):
               yield span


   _hdf5_tracer = _LocalHdf5Tracer()

Every span the engine emits is therefore wrapped in
``local_tracing``. That call sets the per-context MPI
communicator used by ``BsbTracer`` for span broadcasts to
``MPI.COMM_SELF`` (a single-rank communicator). Spans created inside the block
therefore do not trigger any cross-rank broadcast.

Why the broadcast had to go
---------------------------

By default ``BsbTracer`` does a collective broadcast on the first span of
a trace so that every rank's downstream spans share the same trace id. That
default is the right call for cluster-wide BSB phases (the run as a whole,
each pipeline phase), where every rank executes the same sequence of traced
operations.

It is the wrong call for engine spans, because engine operations are
**per-rank divergent**:

* Workers all run ``PlacementJob``, but they get different chunks. Their
  ``hdf5.append_data`` calls fire at different times and in different counts.
* Reads from rank 0 (the scheduler) and from a worker are completely
  uncoordinated.
* MPILock is the synchronisation primitive that lets ranks share the file,
  not a collective. There is no "first hdf5 span per rank" that lines up.

If the engine emitted spans through the default tracer, rank 0 would block on
``bcast`` waiting for a worker that took a different code path, and the
worker would block on ``bcast`` waiting for rank 0. The first
divergence-and-trace produces a hang.

Wrapping every engine span in ``local_tracing`` cuts the bcast out for
engine spans only. A cross-rank parent set above the engine (e.g. by a
``run_placement`` collective span) is still inherited because
``local_tracing`` only changes the *broadcast* communicator, not the OTel
parent-span context.

Adding new spans
----------------

Use the local tracer for anything that wraps an HDF5 access:

.. code-block:: python

   with _hdf5_tracer.trace(
       "hdf5.my_op",
       attributes={"hdf5.path": self._path, "hdf5.mode": "r"},
   ):
       ...

The convention for span attributes:

* ``hdf5.path`` (string): the HDF5 path the operation touches.
* ``hdf5.mode`` (``r`` or ``a``): the open mode the span runs under.
* ``hdf5.rows_added`` (int): for append spans, the number of rows written.
* ``mpi.rank`` / ``mpi.size``: added automatically by ``BsbTracer.trace``;
  do not set them manually.

What gets emitted automatically
-------------------------------

The ``handles_handles`` decorator emits:

* ``hdf5.<method_name>`` covering the function body (including the wait for
  the MPI lock and the file open).
* ``hdf5.file.open`` covering only the ``h5py.File`` lifetime, via the
  ``_SpannedHandle`` wrapper. The two spans always nest.

A read path therefore produces:

::

   mpilock.read                              (acquire + release)
   └── hdf5.<method_name>                    (whole body)
       └── hdf5.file.open                    (h5py.File lifetime)
           └── ...whatever the method does

When nested ``handles_handles`` calls reuse the ambient handle (the discipline
in :doc:`handles`), or many top-level calls run inside a
:meth:`~bsb_hdf5.HDF5Engine.read_scope` / :meth:`~bsb_hdf5.HDF5Engine.write_scope`
block, those calls add their own ``hdf5.<method_name>`` spans inside the open
handle's span, **without** another ``mpilock.read`` or ``hdf5.file.open``. The
trace shape tells you immediately whether reuse is working: many sibling
``hdf5.file.open`` spans where you expected one means a call escaped the ambient
handle (for example an undecorated path that opened its own).
