###############
Post Processing
###############

The BSB allows users to implement and register custom functions that run between
workflow stages to perform additional tasks that are not covered by the
built-in steps.

Users can register postprocessing hooks that execute after either the
**Placement** or **Connectivity** stages.

AfterPlacementHook
==================

`AfterPlacementHook` registers a function that runs after the placement step
and before the connectivity step.

The abstract base class is provided at:
:class:`bsb:bsb.postprocessing.AfterPlacementHook`.

To create a custom hook, subclass `AfterPlacementHook` and implement the
:guilabel:`postprocess` method, which defines the logic executed at this stage.

**Examples**

.. code-block:: python

    class MyAfterPlacement(AfterPlacementHook):
        def postprocess(self):
            # Implement post-placement logic here


AfterConnectivityHook
=====================

The :class:`AfterConnectivityHook <bsb:bsb.postprocessing.AfterConnectivityHook>`
operates similarly to `AfterPlacementHook`, but is executed **only after
the connectivity stage is complete**.

The BSB provides several built-in hooks, including the following.

FuseConnectivity
----------------

This hook allows users to create new connections by merging existing
connectivity sets, effectively bypassing intermediate cell types.

For example, given a chain::

    cell_a -> cell_b -> cell_c -> cell_d

you can directly connect ``cell_a`` to ``cell_d`` while bypassing
``cell_b`` and ``cell_c``.

Two strategies are supported:

MergeConnections
^^^^^^^^^^^^^^^^

The :class:`bsb:bsb.postprocessing.MergeDirect` strategy accepts a list of
connectivity sets to merge. It reconstructs the connectivity tree defined by
these sets and creates a new connectivity set for each root–leaf pair.

This strategy does **not** allow merging discontinuous connectivity lists
(e.g., ``[cell_a -> cell_b, cell_d -> cell_e]``).

**Parameters**

* ``connections`` – List of connectivity sets to merge.

**Examples**


.. tab-set::

   .. tab-item:: JSON

      .. code-block:: json

          "after_connectivity": {
              "new_connection": {
                  "strategy": "merge_connections",
                  "connections": ["my_connections_list"]
              }
          }

   .. tab-item:: Python

      .. code-block:: python

          config.after_connectivity = dict(
              new_connection=dict(
                  strategy="merge_connections",
                  connections=["my_connections_list"],
              )
          )


IntermediateRemoval
^^^^^^^^^^^^^^^^^^^

The :class:`bsb:bsb.postprocessing.IntermediateRemoval` strategy removes specified
intermediate cell types from the connection path when generating new direct
connections.

**Parameters**

* ``cell_list`` – List of cell types to bypass.

**Examples**

.. tab-set::

   .. tab-item:: JSON

      .. code-block:: json

          "after_connectivity": {
              "new_connection": {
                  "strategy": "intermediate_removal",
                  "cell_list": ["list_of_cell_to_be_excluded"]
              }
          }

   .. tab-item:: Python

      .. code-block:: python

          config.after_connectivity = dict(
              new_connection=dict(
                  strategy="intermediate_removal",
                  cell_list=["list_of_cell_to_be_excluded"],
              )
          )