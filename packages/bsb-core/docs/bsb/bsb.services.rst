bsb.services package
====================

The ``bsb.services`` modules are *reference stubs* that document the contract
every provider must satisfy. The actual runtime modules are installed by
``bsb.services.__init__`` from the configured providers in
:mod:`bsb._providers`.

Submodules
----------

bsb.services.mpi module
^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: bsb.services.mpi
   :members:
   :undoc-members:
   :show-inheritance:

bsb.services.mpilock module
^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: bsb.services.mpilock
   :members:
   :undoc-members:
   :show-inheritance:

bsb.services.pool module
^^^^^^^^^^^^^^^^^^^^^^^^

.. automodule:: bsb.services.pool
   :members:
   :undoc-members:


.. The following stub is required to cover a docstring error because
   `WorkflowError` inherits from a generic in `exceptiongroup` that uses
   this typevar.

.. class:: _ExceptionT_co
