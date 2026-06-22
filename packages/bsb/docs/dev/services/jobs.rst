Jobs and the JobPool
####################

The :mod:`bsb.jobs` module is the framework's **workflow layer**: it owns
job submission, dependency tracking, status notifications and pool-managed
caching. It sits on top of the :doc:`pool service <pool>` (the thin
concurrent executor) but adds everything that makes a "pool" actually
useful for a BSB compile run.

.. note::

   This is the *thick* counterpart to the *thin* :doc:`pool service <pool>`.
   The pool service answers "give me futures for callables". The JobPool
   answers "compile a network by orchestrating placement, connectivity,
   post-processing and caching across ranks."

Entry points
============

Top-level::

  from bsb.jobs import (
      JobPool,
      Job, PlacementJob, ConnectivityJob, FunctionJob,
      JobStatus, PoolStatus, PoolProgressReason,
      PoolProgress, PoolJobAddedProgress, PoolJobUpdateProgress, PoolStatusProgress,
      Workflow, SubmissionContext, WorkflowError,
      Listener, NonTTYTerminalListener, TTYTerminalListener,
      pool_cache,
  )

The convenience entry point is :meth:`Scaffold.create_job_pool
<bsb.core.Scaffold.create_job_pool>`, which constructs a pool bound to the
scaffold and pre-registers a sensible default listener.

Quick start
===========

The recommended way to use a JobPool is via the scaffold's context manager:

.. code-block:: python

  from bsb import from_storage

  network = from_storage("example.hdf5")
  with network.create_job_pool() as pool:
      if pool.is_main():
          # Only the main node schedules
          for component in network.placement.values():
              component.queue(pool)
      # Every rank participates in execute()
      pool.execute()

The pool must be used as a context manager. Entering binds the scaffold
as the *owner*, creates a temporary directory for result spillover, and
transitions the pool to :attr:`PoolStatus.SCHEDULING`. Exiting tears
those down — using a pool whose context has exited raises
:class:`~bsb.exceptions.JobPoolContextError`.

Status model
============

PoolStatus
----------

A pool moves through three states during its lifetime:

* :attr:`PoolStatus.SCHEDULING` — set on context entry. Jobs may be
  ``queue``-d and schedulers may be ``schedule``-d.

* :attr:`PoolStatus.EXECUTING` — set inside :meth:`execute`. The driver
  is now actively running jobs.

* :attr:`PoolStatus.CLOSING` — set after execution finishes, before any
  ``raise_unhandled`` runs. Listeners use this to flush totals.

JobStatus
---------

Every :class:`Job` carries one of these:

* :attr:`JobStatus.PENDING` — job is in the queue but waiting on its
  dependencies to complete (or for the parallel pool to actually open).
* :attr:`JobStatus.QUEUED` — job has been handed to the underlying
  executor and is in the queue.
* :attr:`JobStatus.RUNNING` — the worker started running the job.
* :attr:`JobStatus.SUCCESS` — the handler returned normally; the result
  is spilled to disk and accessible via :attr:`Job.result`.
* :attr:`JobStatus.FAILED` — the handler raised. :attr:`Job.error`
  carries the exception.
* :attr:`JobStatus.CANCELLED` — the job was explicitly cancelled (e.g.
  because a dependency failed). :attr:`Job.error` is a
  :class:`~bsb.exceptions.JobCancelledError`.
* :attr:`JobStatus.ABORTED` — the worker was killed.

Job submission
==============

The JobPool exposes three convenience submission methods plus a generic
queue:

.. py:method:: JobPool.queue(f, args=None, kwargs=None, deps=None, **context)
   :no-index:

   Submit a :class:`FunctionJob` wrapping a free function ``f``. ``f`` is
   called as ``f(scaffold, *args, **kwargs)`` on the worker. ``context``
   keyword arguments are stored on the job's
   :class:`SubmissionContext`.

.. py:method:: JobPool.queue_placement(strategy, chunk, deps=None)
   :no-index:

   Submit a :class:`PlacementJob` for a single
   :class:`~bsb.placement.strategy.PlacementStrategy` running on one
   chunk.

.. py:method:: JobPool.queue_connectivity(strategy, pre_roi, post_roi, deps=None)
   :no-index:

   Submit a :class:`ConnectivityJob` for a
   :class:`~bsb.connectivity.strategy.ConnectivityStrategy` running on a
   pair of regions of interest.

``deps`` accepts an iterable of :class:`Job` instances. The new job will
not be enqueued on the underlying executor until every dep transitions to
:attr:`JobStatus.SUCCESS`; if any dep ends in
:attr:`JobStatus.FAILED` / ``CANCELLED`` / ``ABORTED``, the dependent
job is cancelled with reason ``"Job killed for dependency failure"``.

Scheduling threads
==================

Pools can stream jobs onto the queue *while* execution is already running.
This matters because, in real compiles, scheduling jobs (walking the
component tree, computing chunks, etc.) is itself expensive enough that
you don't want to block worker startup on it.

.. py:method:: JobPool.schedule(nodes, scheduler=None)
   :no-index:

   Spawn a daemon thread that walks ``nodes`` and calls
   ``scheduler(node)`` on each (default scheduler: ``node.queue(self)``).
   The thread is tracked via a future stored in
   :attr:`JobPool.scheduling`; the driver loop in :meth:`execute` waits
   on it alongside actual job futures.

.. code-block:: python

  with network.create_job_pool() as pool:
      if pool.is_main():
          pool.schedule([*network.placement.values()])
      pool.execute()

.. warning::

   Pass a **topologically sorted** iterable. ``schedule`` only checks
   ``depends_on`` between *nodes* (to skip submitting dependents of
   failed predecessors); it doesn't reorder them, and the
   inter-job dependency tracking only kicks in once both jobs exist.

Per-node scheduler errors are captured in a
:class:`SubmissionContext` and surfaced as
:class:`~bsb.exceptions.JobSchedulingError` instances inside the eventual
:class:`WorkflowError`.

Execution
=========

.. py:method:: JobPool.execute(return_results=False)
   :no-index:

   Block until every job and every scheduler has completed. If
   ``return_results`` is true, returns a ``{job: job.result}`` dict for
   every job that ended in :attr:`JobStatus.SUCCESS`.

Internally the pool dispatches to one of two drivers:

* **Serial driver** (``size == 1``) — runs each job in-process through
  :meth:`Job.run`, ticking listeners between jobs. Job dependencies are
  honored by the order things were queued.

* **Parallel driver** (``size > 1``) — constructs a
  :class:`~bsb.services.pool.PoolExecutor` via the resolved
  :doc:`pool service <pool>`, enqueues every ready job, then
  :func:`concurrent.futures.wait`-loops while either schedulers or
  pending/queued jobs remain.

  Workers (where :meth:`PoolExecutor.is_worker` is true) fall through
  the constructor and never enter the driver — they block inside the
  executor for tasks dispatched from rank 0, then return when the master
  ``shutdown``-s the pool.

  On any exception in the driver (including ``SystemExit`` and
  ``KeyboardInterrupt``) the pool broadcasts an "abort" flag so workers
  raise a :class:`WorkflowError` on their side too.

The driver always finishes by calling
``self._mpipool.shutdown(wait=False, cancel_futures=True)`` and
broadcasting whether any unhandled errors remain.

The Job class hierarchy
=======================

Job (abstract)
--------------

.. py:class:: Job
   :no-index:

   Base class for everything that goes onto the pool. Concrete subclasses
   override :meth:`execute` to define how the job runs *on the worker*.

   Public attributes:

   * :attr:`Job.status` — current :class:`JobStatus`.
   * :attr:`Job.result` — the unpickled return value of a successful
     job. Spilled to a temp file under
     :meth:`JobPool.get_tmp_folder`; raises
     :class:`~bsb.exceptions.JobPoolError` if the job didn't succeed.
   * :attr:`Job.error` — the captured exception on failure / cancel.
   * :attr:`Job.name` / :attr:`Job.description` — formatted from the
     :class:`SubmissionContext`.
   * :attr:`Job.submitter` / :attr:`Job.context` — submission metadata.

   Public methods:

   * :meth:`Job.serialize` — return the ``(class_name, args, kwargs)``
     triple that gets pickled and shipped to the worker. The class name
     selects the static :meth:`execute` handler on the worker side.
   * :meth:`Job.execute` — static abstract method; the actual handler.
     Called on the worker with ``(scaffold, args, kwargs)``.
   * :meth:`Job.run(timeout=None)` — serial-driver path: run the
     handler on the *current* process in a daemon thread (so listeners
     can keep ticking). Returns ``True`` while the thread is still
     alive, ``False`` once done.
   * :meth:`Job.on_completion(cb)` — register a callback fired with the
     job on completion (success or failure).
   * :meth:`Job.cancel(reason=None)` — transition to
     :attr:`JobStatus.CANCELLED` and try to cancel the underlying
     future.
   * :meth:`Job.change_status(status)` — internal state transition;
     also posts a :class:`PoolJobUpdateProgress` notification.

PlacementJob
------------

.. py:class:: PlacementJob
   :no-index:

   Wraps a single chunk of a placement strategy. Worker side resolves the
   strategy by name via ``job_owner.placement[name]`` and runs
   ``place(chunk, indicators, **kwargs)``. Cache items are pre-collected
   from the strategy via :func:`get_node_cache_items`.

ConnectivityJob
---------------

.. py:class:: ConnectivityJob
   :no-index:

   Wraps a chunk pair of a connectivity strategy. Worker side resolves
   ``job_owner.connectivity[name]`` and runs
   ``connect(*collections, **kwargs)`` where the collections come from
   :meth:`ConnectivityStrategy._get_connect_args_from_job`.

FunctionJob
-----------

.. py:class:: FunctionJob
   :no-index:

   Wraps an arbitrary callable. ``f`` is packed into the first arg slot
   so the worker can unpack it; submitter defaults to ``f`` itself when
   none was given in ``context``.

Listeners
=========

A *listener* is a callable ``listener(progress: PoolProgress) -> bool | None``
that the pool calls every time a notification is posted. The return value
matters: a truthy return marks an error notification as **handled**, so it
is not later re-raised as part of the :class:`WorkflowError`.

Listeners may also be context managers, in which case the pool's
``ExitStack`` enters them on context entry and exits them on context exit
— the lifecycle binding is automatic.

.. py:class:: Listener
   :no-index:

   Abstract base. Subclasses implement
   ``__call__(progress)``.

Builtin listeners
-----------------

.. py:class:: NonTTYTerminalListener
   :no-index:

   Plain-line printer suitable for log files or non-interactive shells.
   Emits one line per :attr:`JobStatus` change and a "Progress ping" on
   :attr:`PoolProgressReason.MAX_TIMEOUT_PING`.

.. py:class:: TTYTerminalListener
   :no-index:

   Rich terminal UI built on :mod:`blessed` and :mod:`dashing`. Renders
   a full-screen progress dashboard at ``fps`` updates per second on
   rank 0; on other ranks the listener is a no-op.

   The :meth:`Scaffold.create_job_pool` factory picks between the two
   automatically: ``TTYTerminalListener(fps=25)`` when stdout is a real
   terminal (and ``os.get_terminal_size()`` is non-empty), otherwise
   ``NonTTYTerminalListener``.

Adding a listener
-----------------

.. code-block:: python

  import time
  from bsb.jobs import PoolProgressReason, PoolStatus

  _t = None
  def report_time_elapsed(progress):
      global _t
      if progress.reason == PoolProgressReason.POOL_STATUS_CHANGE:
          if progress.status == PoolStatus.SCHEDULING:
              _t = time.time()
          elif progress.status == PoolStatus.CLOSING:
              print(f"Pool execution finished. {time.time() - _t:.2f}s elapsed.")
      # Returning falsy means: don't claim to have handled any error.

  with network.create_job_pool() as pool:
      pool.add_listener(report_time_elapsed)
      pool.queue(lambda scaffold: time.sleep(2))
      pool.execute()

Listeners are also how the workflow layer surfaces the **fail-fast** flag.
If ``JobPool(fail_fast=True)`` is set, every notify cycle that finds
unhandled errors immediately raises :class:`WorkflowError` instead of
collecting them until the end.

.. _caching:

Pool-managed caching
====================

The motivation: in a parallel workflow, naive memoization (e.g.
:func:`functools.cache`) keeps cached values alive for the entire process
lifetime. On a worker that did one placement job two hours ago, that
cached `~6 GB` voxel array is still pinned.

The JobPool tracks, per running job, what *cache identities* it still
needs. As jobs finish, the set of needed identities shrinks, and the pool
runs the cleanup hooks for any identity no longer claimed by any
in-flight job.

The :func:`pool_cache` decorator
--------------------------------

.. py:function:: pool_cache(caching_function)

   Decorate a method of a ``@config.node``-decorated class to make its
   results live as long as any pool job still needs them, and no longer.

   .. code-block:: python

     from bsb import PlacementStrategy, config, pool_cache

     @config.node
     class MyStrategy(PlacementStrategy):
         @pool_cache
         def heavy_calculations(self):
             return 5 + 5

         def place(self, chunk, indicators):
             # ``heavy_calculations`` is called at most once per worker,
             # and freed when the last claiming job finishes.
             for i in range(1000):
                 self.heavy_calculations()

   Underneath this is a :func:`functools.cache` whose registered cleanup
   is ``cache_clear``. The first call registers the cleanup on the
   scaffold's ``_pool_cache`` map; subsequent calls hit the cache.

How identities are computed
---------------------------

Each ``@pool_cache``-d method gets a stable ``get_pool_cache_id(node)``
hash derived from ``f"{node.get_node_name()}.{method.__name__}"``,
folded through :func:`zlib.crc32`. This is what the pool tracks across
ranks.

When a job is submitted (via :class:`PlacementJob` / :class:`ConnectivityJob`),
:func:`get_node_cache_items` walks the submitter's config subtree and
collects every cache id reachable from it. That list is attached to the
job as ``_cache_items``.

How identities are propagated across ranks
------------------------------------------

The pool maintains an MPI window over a fixed-size ``uint64`` buffer
(:attr:`JobPool._cache_buffer`, 1000 slots). On rank 0:

* :meth:`JobPool._update_cache_window` is called whenever a job finishes.
  It computes the union of ``_cache_items`` across every queued/running
  job, writes them into the window buffer under
  :meth:`MPI.Win.Lock(0)`, and unlocks.

On workers, every job's dispatcher calls
:meth:`JobPool._read_required_cache_items`, which RMA-reads the window
buffer (locked, ``UINT64_T``-typed). The dispatcher then calls
:func:`free_stale_pool_cache` to drop any cleanup hook whose id is no
longer in the current set.

Two side effects worth knowing about:

1. The buffer is fixed at 1000 entries. If a workflow ever has more than
   1000 simultaneously-active cache ids it will silently lose tracking.
2. The window read uses ``mpi4py.MPI.UINT64_T`` directly — the pool
   service abstraction stops at job submission; the cache-coherency
   channel is bound to mpi4py.

Workers also free *all* cache when they bail out early via
:meth:`PoolExecutor.is_worker` short-circuit: ``free_stale_pool_cache(self.owner, set())``.

Errors and exception aggregation
================================

.. py:class:: WorkflowError
   :no-index:

   A :class:`exceptiongroup.ExceptionGroup` containing every unhandled
   error from a pool's execute call.

* Job errors (the handler raised) are wrapped in
  :class:`JobErroredError` chained from the original exception.
* Scheduling errors (the ``schedule`` thread itself raised) are wrapped
  in :class:`~bsb.exceptions.JobSchedulingError`.
* Both kinds are aggregated and re-raised as a single
  :class:`WorkflowError` at the end of :meth:`execute`.

Listeners can mark an error notification as *handled* by returning a
truthy value from ``__call__``. Unhandled errors:

* Are appended to the pool's internal ``_unhandled_errors`` list during
  :meth:`notify`.
* Cause an immediate :class:`WorkflowError` when ``fail_fast=True``.
* Otherwise surface at end of :meth:`execute` via :meth:`raise_unhandled`.

Cancelled jobs (``JobCancelledError``) are deliberately *not* counted as
errors — cancelling is a normal control flow.

Scaffold integration
====================

.. py:method:: Scaffold.create_job_pool(fail_fast=None, quiet=False)
   :no-index:

   The standard entry point. Allocates a pool id deterministically by
   :meth:`MPI.bcast`-ing ``time.time()`` from rank 0; constructs the
   pool with the current scaffold workflow (if any); and registers
   either the user's listeners (via
   :meth:`Scaffold.register_listener`) or the auto-selected default
   (TTY / non-TTY).

.. py:method:: Scaffold.register_listener(listener, max_wait=None)
   :no-index:

   Register a custom listener that will be wired up by every subsequent
   :meth:`create_job_pool` call. ``max_wait`` lower-bounds the JobPool's
   driver-loop sleep timeout — useful for listeners that want regular
   ticks for animation.

Workflows
=========

A :class:`Workflow` is a tiny helper carrying an ordered list of phase
names (e.g. ``["placement", "connectivity", "after_connectivity"]``). The
JobPool stores one if given via the constructor and exposes the active
phase to listeners via :attr:`PoolProgress.workflow`. The actual phase
advancement happens outside the pool (the scaffold's compile driver
ticks :meth:`Workflow.next_phase` between pool calls).

The TTY listener uses :attr:`Workflow.phase` to print the current phase
banner.

Submission context
==================

Every job carries a :class:`SubmissionContext` with:

* ``submitter`` — the object that submitted the job (typically a config
  node like a placement strategy). Used to derive a display ``name``.
* ``chunks`` — optional iterable of chunks the job operates on, wrapped
  via :func:`bsb.storage._chunks.chunklist`.
* ``context`` — free-form kwargs the submitter wants to thread through.
  Accessible via ``job.context`` or as direct attributes
  (``job.some_key`` works because :class:`SubmissionContext` overrides
  ``__getattr__``).

Notification system
===================

The pool emits notifications during state changes. Listeners receive one
of:

.. py:class:: PoolProgress
   :no-index:

   Base. ``progress.reason`` is a :class:`PoolProgressReason` enum:

   * :attr:`PoolProgressReason.POOL_STATUS_CHANGE` — emitted as
     :class:`PoolStatusProgress`; carries the new ``status`` and
     ``old_status``.
   * :attr:`PoolProgressReason.JOB_ADDED` — emitted as
     :class:`PoolJobAddedProgress` when a job is ``_put`` onto the
     queue; carries the new ``job``.
   * :attr:`PoolProgressReason.JOB_STATUS_CHANGE` — emitted as
     :class:`PoolJobUpdateProgress` on every
     :meth:`Job.change_status`; carries the job, its new ``status``,
     and its ``old_status``.
   * :attr:`PoolProgressReason.MAX_TIMEOUT_PING` — emitted by
     :meth:`JobPool.ping` when the driver loop's
     :func:`concurrent.futures.wait` timed out with nothing done.
     Used by listeners that want a regular animation tick.

Tally helpers
-------------

Two helpers used by :class:`TTYTerminalListener` to summarise jobs:

* :class:`JobTally` — per-name counter that tracks per-status counts and
  computes ``progress()``, ``finished()``, formatted string, etc.
* :class:`PoolTally` — ``defaultdict[JobTally]`` keyed by job name;
  knows how to sort by progress and compute remaining-time estimates
  from observed per-job runtime durations.

Both are part of the public surface (``bsb.jobs``) so custom listeners
can reuse them.

Edge cases and gotchas
======================

* **Pool must be context-managed.** Calling :meth:`execute` after
  ``__exit__`` (or without entering) raises
  :class:`~bsb.exceptions.JobPoolContextError`.

* **Job results are pickled to disk.** Each successful job dumps its
  return value into the pool's temp directory; :attr:`Job.result`
  re-opens and unpickles on demand. Don't put huge return values
  through the pool — write them to storage from inside the handler.

* **Workers should never call :meth:`execute`** directly: they enter
  the parallel driver, get short-circuited by
  :meth:`PoolExecutor.is_worker`, free their cache and ``return``. The
  master is the one that runs the wait loop.

* **The cache window is fixed-size (1000).** A workflow with more
  active cache identities will silently lose tracking. This is a
  known limit of the current implementation.

* **Cancellation via dependency failure is not "abort".** A job whose
  dep failed transitions to :attr:`JobStatus.CANCELLED` (not
  ``ABORTED``), and its error is a
  :class:`~bsb.exceptions.JobCancelledError`. Listeners treating only
  ``FAILED`` as a problem will miss this. Use the
  :attr:`Job.error` type to disambiguate.

* **Job dependencies are tracked by Job identity, not by name.** Build
  the dependency relationship at submission time (``deps=[other_job]``).
  Cross-pool dependencies are not supported.
