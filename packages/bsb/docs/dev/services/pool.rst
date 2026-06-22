Pool (executor)
###############

The pool service is the **thin** concurrency backend used by the workflow
layer. It is deliberately *not* the place where job dependencies, workflow
phases or pool caching live — that is :doc:`jobs`. The pool service only
answers a much smaller question: "given a callable and arguments, give me
back a future."

Resolved at import time into ``bsb.services.pool``. The primary class is
re-exported as ``bsb.services.Pool``::

  from bsb.services.pool import Pool
  pool = Pool(loglevel=logging.CRITICAL)

Contract
========

A provider module must expose ``Pool``, a class (or callable) returning a
:class:`PoolExecutor`. ``PoolExecutor`` extends
:class:`concurrent.futures.Executor` with two extra hooks that the workflow
layer needs to drive **collective-coordination backends** like
``mpipool.MPIExecutor`` (where rank 0 schedules and other ranks block as
workers).

.. py:method:: PoolExecutor.submit(fn, /, *args, **kwargs) -> concurrent.futures.Future

   Submit ``fn(*args, **kwargs)`` and return a future. Standard
   ``Executor`` semantics.

.. py:method:: PoolExecutor.shutdown(wait: bool = True, *, cancel_futures: bool = False) -> None

   Stop accepting submissions. After this call ``open`` must be ``False``.

.. py:attribute:: PoolExecutor.open
   :type: bool

   ``True`` while the pool accepts submissions, ``False`` after
   :meth:`shutdown`.

.. py:method:: PoolExecutor.is_worker() -> bool

   For *collective* backends (where every rank in the parallel world
   enters the constructor, but only one schedules), return ``True`` on the
   non-scheduler ranks. For *shared-submit* backends
   (``multiprocessing``, in-process), always return ``False``.

   The thick :class:`~bsb.jobs.JobPool` relies on this to short-circuit
   workers out of the scheduling loop: after constructing the executor,
   workers immediately fall through into "wait-for-shutdown" mode and
   never enter the rank-0 driver code.

Builtin providers
=================

mpipool
-------

Implementation: :mod:`bsb._providers.pool.mpipool` (loaded by
``mpipool_loader:load``).

Wraps ``mpipool.MPIExecutor`` directly — the existing JobPool driver was
built against this API, so the provider barely needs to add anything beyond
plumbing the ``loglevel`` / ``debug`` kwargs:

.. code-block:: python

   class Pool(mpipool.MPIExecutor):
       def __init__(self, *, loglevel=None, debug=False, **kwargs):
           if debug:
               mpipool.enable_serde_logging()
           if loglevel is not None:
               kwargs.setdefault("loglevel", loglevel)
           super().__init__(**kwargs)

* ``is_worker()`` comes from ``MPIExecutor`` and returns ``True`` on all
  non-rank-0 ranks.
* ``open`` reflects the executor's lifecycle.
* Skipped if ``mpipool`` is not installed.

serial
------

Implementation: :mod:`bsb._providers.pool.serial`.

A synchronous in-process executor. ``submit()`` runs the callable
immediately and returns a completed future:

.. code-block:: python

   class Pool(concurrent.futures.Executor):
       def submit(self, fn, /, *args, **kwargs):
           ...
           result = fn(*args, **kwargs)
           future.set_result(result)
           return future

* ``is_worker()`` always returns ``False``.
* ``open`` is ``True`` until ``shutdown`` flips it.
* Useful as a no-dependency fallback and for tests.

.. note::

   The current :class:`~bsb.jobs.JobPool` only consults the pool service
   when running with ``MPI.get_size() > 1``. In single-rank mode it runs
   jobs through :meth:`Job.run` directly, never touching ``Pool``. The
   ``serial`` provider therefore mostly exists as a documented fallback —
   the JobPool will still execute jobs without it, by virtue of the
   parallel branch never firing.

Usage
=====

Direct use of the executor::

   from bsb.services.pool import Pool

   with Pool() as pool:
       futures = [pool.submit(work, i) for i in range(10)]
       results = [f.result() for f in futures]

Driving a collective backend safely::

   from bsb.services.pool import Pool

   pool = Pool(loglevel=logging.CRITICAL)
   if pool.is_worker():
       # Workers must not enter scheduling code. They block inside the
       # executor constructor until the master shuts down.
       return

   try:
       schedule_jobs(pool)
   finally:
       pool.shutdown(wait=False, cancel_futures=True)

Constructor kwargs
==================

The current contract passes two kwargs to ``Pool()`` from the workflow
layer:

* ``loglevel`` — a :mod:`logging` level int.
* ``debug`` — a bool that turns on serialization debugging for backends
  that support it.

Providers are free to accept additional kwargs but should at minimum
tolerate (and either honour or ignore) the two above. The provided
``serial`` backend ignores both.

Adding a backend
================

The most common reason to add a new provider is to swap MPI-based
parallelism for something else: ``concurrent.futures.ProcessPoolExecutor``
for local-only runs, ``dask.distributed.Client`` for cluster scheduling,
or a custom backend. See :doc:`providers` for the entry-point conventions;
the only contract obligation is the protocol above.
