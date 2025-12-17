##############################
List of AfterConnectivityHooks
##############################


MergeConnections
----------------

The :class:`MergeDirect <bsb:bsb.postprocessing.MergeDirect>` strategy accepts a list of
connectivity sets to merge. It reconstructs the connectivity tree defined by
these sets and creates a new connectivity set for each root–leaf pair.
For example, given a chain::

    cell_a -> cell_b -> cell_c -> cell_d

you can directly connect ``cell_a`` to ``cell_d`` while bypassing
``cell_b`` and ``cell_c``.

This strategy does **not** allow merging discontinuous connectivity lists
(e.g., ``[cell_a -> cell_b, cell_d -> cell_e]``).
If the merge results in a cell being connected to itself (i.e., a loop),
an error is raised.

**Parameters**

* ``connections`` – List of connectivity sets to merge.

**Examples**


.. tab-set::

   .. tab-item:: JSON

      .. code-block:: json

          "after_connectivity": {
              "new_connection": {
                  "strategy": bsb.postprocessing.MergeDirect,
                  "connections": ["my_connections_list"]
              }
          }

   .. tab-item:: Python

      .. code-block:: python

          config.after_connectivity = dict(
              new_connection=dict(
                  strategy=bsb.postprocessing.MergeDirect,
                  connections=["my_connections_list"],
              )
          )

If the connectivity tree contains a single root and a single leaf, the hook name is used as the name of the resulting connectivity set.
If multiple roots and/or multiple leaves are present, each resulting connectivity set is named using the pattern
`<root_name>_to_<leaf_name>`.

Example

Consider the connectivity tree A + B → C → D + F:

.. tab-set::

.. tab-item:: JSON

  .. code-block:: json

     "after_connectivity": {
         "new_connection": {
             "strategy": bsb.postprocessing.MergeDirect,
             "connections": ["A_to_C", "B_to_C", "C_to_D", "C_to_F"]
         }
     }


.. tab-item:: Python

  .. code-block:: python

     config.after_connectivity = dict(
         new_connection=dict(
             strategy=bsb.postprocessing.MergeDirect,
             connections=["A_to_C", "B_to_C", "C_to_D", "C_to_F"],
         )
     )


This configuration generates four connectivity sets, named:
 * A_to_D
 * A_to_F
 * B_to_D
 * B_to_F

IntermediateBypass
-------------------

The :class:`IntermediateBypass <bsb:bsb.postprocessing.IntermediateBypass` strategy removes specified
intermediate cell types from the connection path when generating new direct
connections.
For example, given a chain::

    cell_a -> cell_b -> cell_c -> cell_d

if cell_c is selected it will create a direct connection between cell_b and cell_d.

**Parameters**

* ``cell_list`` – List of cell types to bypass.

**Examples**

.. tab-set::

   .. tab-item:: JSON

      .. code-block:: json

          "after_connectivity": {
              "new_connection": {
                  "strategy": bsb.postprocessing.IntermediateBypass,
                  "cell_list": ["list_of_cell_to_be_excluded"]
              }
          }

   .. tab-item:: Python

      .. code-block:: python

          config.after_connectivity = dict(
              new_connection=dict(
                  strategy=bsb.postprocessing.IntermediateBypass,
                  cell_list=["list_of_cell_to_be_excluded"],
              )
          )