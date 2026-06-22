Provider resolution
###################

This page describes the mechanics behind every BSB service: how a service is
declared, how providers register, how the framework picks one at import time,
and what a third-party package needs to do to ship its own.

The pattern
===========

A **service** is a name (``mpi``, ``mpilock``, ``pool``, …) that maps to a
submodule of :mod:`bsb.services`. The source file at
``bsb/services/<name>.py`` is a **reference stub**: it declares the contract
every provider must satisfy (typically as :class:`typing.Protocol` classes and
type aliases) but is *never executed at runtime*.

When :mod:`bsb.services` is imported, its ``__init__`` enumerates the stubs,
reads the user's preferred provider list, walks the
``bsb.providers.<name>`` entry-point group, and **swaps the resolved provider
module into** ``sys.modules['bsb.services.<name>']`` *before* any consumer can
``import bsb.services.<name>``. The stub on disk only exists for IDEs and
type-checkers; the symbols a consumer actually imports come from the
provider.

The resolved provider's primary symbol (``MPI``, ``MPILock``, ``Pool``) is
also re-exported on :mod:`bsb.services` itself, so
``from bsb.services import MPI`` keeps working.

User preference
===============

Each service has a corresponding option that takes a comma-separated, ordered
list of provider names. The resolver tries them left to right; the first
that successfully loads wins. If the list exhausts with no usable provider,
the framework refuses to start and raises
:class:`~bsb.exceptions.DependencyError` listing what was tried.

.. list-table::
   :header-rows: 1
   :widths: 18 24 18 40

   * - Service
     - Environment variable
     - Project option
     - Default

   * - MPI
     - ``BSB_PROVIDE_MPI``
     - ``provide_mpi``
     - ``mpi4py,serial``

   * - MPILock
     - ``BSB_PROVIDE_MPILOCK``
     - ``provide_mpilock``
     - ``mpilock,serial``

   * - Pool
     - ``BSB_PROVIDE_POOL``
     - ``provide_pool``
     - ``mpipool,serial``

.. note::

  Because resolution happens at import time, providers can be selected only
  from the environment or the project file — not from script-level
  ``bsb.options.*`` assignments after import, and not from the CLI.

Inspecting the active provider
==============================

You can ask the resolver which provider succeeded:

.. code-block:: python

  import bsb.services
  bsb.services.get_resolved("mpi")      # e.g. "mpi4py"
  bsb.services.get_resolved("pool")     # e.g. "mpipool"

Entry-point convention
======================

Providers register their modules in the ``bsb.providers.<service>``
entry-point group. The **value** of each entry point can be one of two
shapes:

1. **A plain module** — imported directly and installed as the provider.
   Use this when importing the module is cheap and has no side effects::

       [project.entry-points."bsb.providers.mpi"]
       serial = "bsb._providers.mpi.serial"

2. **A callable returning a module** — used when probing the backend
   requires side-effectful imports (e.g. ``import mpi4py.MPI`` triggers MPI
   initialization). The callable must raise
   :class:`~bsb.exceptions.ProviderUnavailableError` if the backend is
   missing or unsuitable; otherwise it imports and returns the heavy
   provider module::

       [project.entry-points."bsb.providers.mpi"]
       mpi4py = "bsb._providers.mpi.mpi4py_loader:load"

The resolver inspects the loaded value: if it is callable (and not itself a
module), it is invoked; otherwise it is used as-is.

The callable form is what makes the probe-before-commit guarantee possible.
A provider whose **module body** raises ``ImportError`` at top level
*cannot* be tried-and-discarded — the import has already crashed the
process. Always isolate side-effectful imports behind a loader function.

Anatomy of a provider package
=============================

A complete third-party provider that adds a Dask-backed
:doc:`pool service <pool>` to the framework looks like:

.. code-block:: text

    bsb-dask/
      pyproject.toml
      bsb_dask/
        __init__.py
        pool.py            # heavy: imports dask, exposes Pool
        pool_loader.py     # cheap: probes dask, returns pool

.. code-block:: python

  # bsb_dask/pool_loader.py
  from bsb.exceptions import ProviderUnavailableError

  def load():
      try:
          import dask          # noqa: F401  - probe only
      except ImportError as exc:
          raise ProviderUnavailableError("dask is not installed") from exc
      from . import pool as provider
      return provider

.. code-block:: python

  # bsb_dask/pool.py
  import concurrent.futures
  from dask.distributed import Client

  class Pool(concurrent.futures.Executor):
      def __init__(self, **kwargs):
          self._client = Client(**kwargs)
          self._open = True

      @property
      def open(self):
          return self._open

      def is_worker(self):
          return False

      def submit(self, fn, /, *args, **kwargs):
          return self._client.submit(fn, *args, **kwargs)

      def shutdown(self, wait=True, *, cancel_futures=False):
          self._open = False
          self._client.close()

.. code-block:: toml

  # bsb-dask/pyproject.toml
  [project.entry-points."bsb.providers.pool"]
  dask = "bsb_dask.pool_loader:load"

End users opt in by setting ``BSB_PROVIDE_POOL=dask`` (or
``dask,serial`` to fall back to the in-process executor).

Builtin providers
=================

``bsb-core`` ships defaults for each service under :mod:`bsb._providers`:

.. list-table::
   :header-rows: 1
   :widths: 18 24 58

   * - Service
     - Provider
     - Notes

   * - mpi
     - ``mpi4py``
     - Real MPI via ``mpi4py.MPI.COMM_WORLD``. Skipped if ``mpi4py`` is
       not installed.

   * - mpi
     - ``serial``
     - Single-rank emulator. Refuses to load if an ``MPI``-style env var is
       present and ``BSB_IGNORE_PARALLEL`` is unset, to catch silent
       degradation under ``mpirun``.

   * - mpilock
     - ``mpilock``
     - Re-exports the ``mpilock`` package. Skipped if missing.

   * - mpilock
     - ``serial``
     - Noop locks plus :class:`~bsb._providers.mpilock.serial.Fence` for
       single-write fencing.

   * - pool
     - ``mpipool``
     - Wraps ``mpipool.MPIExecutor``. Skipped if missing.

   * - pool
     - ``serial``
     - In-process synchronous executor (returns completed futures).

Failure modes
=============

* **Backend not installed** — the loader raises
  :class:`~bsb.exceptions.ProviderUnavailableError`; the resolver records
  it and moves to the next candidate.

* **No entry point for a requested name** — recorded as
  ``<name> (no entry point registered)`` and skipped.

* **Side-effectful import error in a plain-module entry point** — the
  exception propagates through ``ep.load()``;
  :class:`~bsb.exceptions.ProviderUnavailableError` is caught and treated
  as a normal "next candidate" signal, anything else aborts.

* **All candidates exhausted** — the resolver raises
  :class:`~bsb.exceptions.DependencyError` whose message lists every name
  that was tried and why it failed.
