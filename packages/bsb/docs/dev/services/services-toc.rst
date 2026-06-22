Services
########

The BSB ships a small set of **services** — thin abstractions over swappable
backends that the framework and downstream packages can rely on without
caring which package actually provides them. Each service is a *contract*
plus a registry of *providers*; at import time, the framework picks the first
provider the user prefers that is actually usable, and installs it into the
``bsb.services.<name>`` namespace.

Today the framework defines three services:

* :doc:`mpi` — MPI communicator and collective primitives.
* :doc:`mpilock` — RMA lock controllers for shared file access.
* :doc:`pool` — the *thin* concurrency executor used by the workflow layer.

Built on top of those, the workflow layer lives in :mod:`bsb.jobs`:

* :doc:`jobs` — :class:`~bsb.jobs.JobPool`, :class:`~bsb.jobs.Job`,
  listeners and :func:`~bsb.jobs.pool_cache`.

If you only want to *use* an existing service, read its page directly.
If you want to *provide a new backend*, start with :doc:`providers`.

.. toctree::
   :maxdepth: 2
   :caption: Services

   providers
   mpi
   mpilock
   pool
   jobs
