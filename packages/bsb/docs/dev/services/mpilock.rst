MPILock
#######

The MPILock service provides cross-rank locking around a shared resource —
typically the storage backend's HDF5 file. Resolved at import time into
``bsb.services.mpilock``; the primary symbol is also re-exported as
``bsb.services.MPILock``.

.. note::

   Depends on the :doc:`MPI service <mpi>`. The serial provider's
   controller pulls its rank/size from :attr:`bsb.services.mpi.MPI`.

Contract
========

A provider module must expose ``MPILock``, an object whose ``sync()`` method
returns a *controller*.

``MPILock.sync(comm=None, master=0) -> Controller``
---------------------------------------------------

Construct a window controller bound to ``comm`` (an MPI communicator object,
not a :class:`MPIService` wrapper) with ``master`` designating the rank
allowed to enter critical sections.

``MPILock(comm=None, master=None) -> Controller``
-------------------------------------------------

The factory is also callable as a shortcut for ``sync``. The real
``mpilock`` package supports both calling conventions; the serial provider
implements them identically.

Controller protocol
-------------------

.. py:attribute:: controller.master
   :type: int

   The rank designated as the lock master.

.. py:attribute:: controller.rank
   :type: int

   The current rank.

.. py:attribute:: controller.closed
   :type: bool

   ``True`` after :meth:`close`.

.. py:method:: controller.close()

   Release the window and mark the controller closed.

.. py:method:: controller.__enter__() / __exit__()

   Context manager that calls :meth:`close` on exit.

.. py:method:: controller.read()

   Return a *read lock* context manager. Block until no writer holds the
   window, then enter shared-read mode. Noop on serial (every rank just
   proceeds).

.. py:method:: controller.write()

   Return a *write lock* context manager. Block until no other reader or
   writer holds the window, then enter exclusive-write mode. Noop on
   serial.

.. py:method:: controller.single_write(handle=None, rank=None)

   Return a context manager that grants exclusive write access to a single
   rank (default: ``master``).

   * On the elected rank, the context body runs and the optional
     ``handle`` (e.g. an open HDF5 file) is yielded.
   * On the other ranks, the body is *not* run; instead the context
     yields a :class:`Fence` (or :class:`_NoHandle` if ``handle`` was
     given), and the body is short-circuited by raising
     :class:`FencedSignal` which the ``__exit__`` quietly swallows.

   Use this to perform "rank 0 writes, everyone else stays out" without
   peppering ``if rank == 0:`` everywhere.

Builtin providers
=================

mpilock
-------

Implementation: :mod:`bsb._providers.mpilock.mpilock` (loaded by
``mpilock_loader:load``). Re-exports the actual ``mpilock`` package
(``mpilock.sync()`` returns a real ``WindowController``).

* Loader probes ``import mpilock`` and raises
  :class:`~bsb.exceptions.ProviderUnavailableError` if missing.

serial
------

Implementation: :mod:`bsb._providers.mpilock.serial`.

* :class:`_MockedWindowController` returns
  :class:`_NoopLock` for ``read``/``write`` (locked context that immediately
  acquires and releases) and a :class:`Fence` / :class:`_NoHandle` for
  ``single_write`` so the same call sites compile in both modes.
* The factory pulls rank/size lazily from
  :attr:`bsb.services.mpi.MPI` to avoid an import cycle.

Usage examples
==============

Default whole-storage lock::

  from bsb.services.mpilock import MPILock
  from bsb.services.mpi import MPI

  controller = MPILock.sync(MPI.get_communicator())
  with controller.write():
      write_to_hdf5_dataset(...)

Single-writer pattern with a handle::

  with controller.single_write(handle=h5file) as h:
      if h is not None:        # elected rank
          h["/dataset"][:] = data

  # Non-elected ranks short-circuit cleanly; only the elected rank executes
  # the body.

Manual fencing::

  with controller.single_write() as fence:
      fence.guard()             # raises FencedSignal on non-elected ranks
      do_exclusive_work()

Caveats
=======

* ``MPILock.sync`` takes the raw communicator object, not the
  :class:`~bsb.services.mpi.MPIService` wrapper. Pass
  ``MPI.get_communicator()``.
* Lock controllers should be ``close()``-d (or used as a context manager).
  In long-running services, leaking controllers can leak ``MPI.Win``
  resources.
* In the serial provider every lock is a noop; correctness in single-rank
  runs relies on there being no other writer. Don't depend on the lock to
  serialize threads in the same process — it doesn't.
