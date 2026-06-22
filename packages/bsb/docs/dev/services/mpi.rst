MPI
###

The MPI service exposes a single communicator wrapper used everywhere the
framework needs collective operations. Resolved at import time into
``bsb.services.mpi``; the primary singleton is also re-exported as
``bsb.services.MPI``::

  from bsb.services.mpi import MPI       # explicit
  from bsb.services import MPI           # re-export
  from bsb import MPI                    # top-level lazy attribute

Contract
========

A provider module must expose two symbols.

``MPI`` — an instance satisfying the protocol below
---------------------------------------------------

.. py:method:: MPI.get_communicator()

   Return the underlying communicator object (e.g. ``mpi4py.MPI.Comm``) or
   ``None`` in the serial provider.

.. py:method:: MPI.get_rank() -> int

   The current process rank. ``0`` on serial.

.. py:method:: MPI.get_size() -> int

   The number of ranks in the communicator. ``1`` on serial.

.. py:method:: MPI.barrier() -> None

   Block until every rank has reached this call. Noop on serial.

.. py:method:: MPI.abort(errorcode: int = 1) -> None

   Tear down the MPI world unconditionally. On serial, prints a marker and
   calls :func:`sys.exit`.

.. py:method:: MPI.bcast(obj, root: int = 0)

   Broadcast ``obj`` from ``root`` to every rank. Returns ``obj`` on serial.

.. py:method:: MPI.gather(obj, root: int = 0) -> list

   Gather ``obj`` from every rank onto ``root``. Returns ``[obj]`` on
   serial.

.. py:method:: MPI.allgather(obj) -> list

   Gather ``obj`` from every rank onto every rank. Returns ``[obj]`` on
   serial.

.. py:method:: MPI.window(buffer)

   Create an RMA window over a buffer. Returns a real ``mpi4py.MPI.Win``
   on parallel runs with ``size > 1``; otherwise returns a mock with
   no-op ``Lock``/``Unlock`` and a ``Get`` that just returns
   ``bufspec[0]``.

.. py:method:: MPI.try_all(default_exception: Exception | None = None)
   :no-index:

   Context manager that collectively re-raises any exception that occurred
   on any rank. After the body returns, exceptions are :meth:`allgather`-ed
   and every rank raises — either its own exception, or
   ``default_exception`` (default ``RuntimeError("An error occurred on a
   different rank")``). Noop on serial.

.. py:method:: MPI.try_main()
   :no-index:

   Context manager that broadcasts exceptions from rank 0 to every other
   rank. Every rank enters the body (the contextlib protocol requires it),
   but only rank 0's exception is broadcast and re-raised everywhere.
   Useful for setup steps that only meaningfully run on the main rank.
   Noop on serial.

``MPIService`` — the wrapper class
----------------------------------

The class that constructs per-communicator wrappers. Some downstream code
(notably storage engines) needs a wrapper bound to a *non-default*
communicator. Calling ``MPIService(comm)`` must return an object with the
same protocol as ``MPI`` but using ``comm`` (a real ``mpi4py.MPI.Comm``)
instead of ``COMM_WORLD``.

The serial provider's ``MPIService`` raises
:class:`~bsb.exceptions.DependencyError` if a non-``None`` ``comm`` is
passed: it has no way to honour a real communicator.

Builtin providers
=================

mpi4py
------

Implementation: :mod:`bsb._providers.mpi.mpi4py` (loaded by
``bsb._providers.mpi.mpi4py_loader:load``).

* Loader probes ``import mpi4py`` (the cheap top-level import) and raises
  :class:`~bsb.exceptions.ProviderUnavailableError` if missing.
* On success it imports the heavy provider, which then imports
  ``mpi4py.MPI`` and creates the singleton ``MPI = MPIService()``.
* The singleton wraps ``COMM_WORLD``; passing a custom ``comm=`` to
  ``MPIService`` selects a different communicator.
* ``window`` falls back to a no-op mock when ``size == 1`` so the same
  user code works on single-rank invocations of an MPI build.

serial
------

Implementation: :mod:`bsb._providers.mpi.serial`.

* All collectives are no-ops or identity operations
  (``bcast`` returns ``obj``, ``gather``/``allgather`` return ``[obj]``,
  ``window`` returns the mock).
* Module import refuses to load if any environment variable contains
  ``mpi`` (case-insensitive) and ``BSB_IGNORE_PARALLEL`` is not set. This
  catches the silent-degradation bug where someone runs
  ``mpirun -n 4 bsb compile`` without ``mpi4py`` installed: instead of
  every rank running independently and corrupting output, the framework
  refuses to start.

  Override with ``BSB_IGNORE_PARALLEL=1`` if you really do want to force
  the serial provider despite the env.

Usage examples
==============

Collective barrier across ranks::

  from bsb.services.mpi import MPI

  MPI.barrier()
  if MPI.get_rank() == 0:
      print(f"All {MPI.get_size()} ranks have arrived.")

Broadcast a computed value::

  result = expensive_computation() if MPI.get_rank() == 0 else None
  result = MPI.bcast(result)

Collective failure handling::

  with MPI.try_all():
      # If any rank raises, every rank re-raises after the block.
      do_something_that_might_fail_on_one_rank()

Main-only setup, fan-out the failure::

  with MPI.try_main():
      if MPI.get_rank() == 0:
          configure_global_state()
      # If rank 0 fails, every rank gets the same exception after exit.

Per-communicator wrapper for storage::

  from bsb.services.mpi import MPIService

  storage_comm = create_sub_communicator(...)   # mpi4py.MPI.Comm
  wrapper = MPIService(storage_comm)
  wrapper.barrier()

Caveats
=======

* The wrapper is **not** a drop-in for ``mpi4py.MPI.Comm``. It uses
  ``get_rank()`` / ``get_size()`` (lowercase) and exposes a deliberately
  small surface. Reach for ``MPI.get_communicator()`` only when you have
  to call something not on the protocol.
* :meth:`MPI.window` returns either a real ``mpi4py.MPI.Win`` or a mock
  with the same three-method shape (``Get``, ``Lock``, ``Unlock``). It
  does not cover the full ``Win`` API.
* Provider selection is import-time. Setting ``BSB_PROVIDE_MPI`` *after*
  ``import bsb`` has no effect.
