###############
Post processing
###############

The BSB allows users to implement and register custom functions that run between
workflow stages to perform additional tasks that are not covered by the
built-in steps.

Users can register postprocessing hooks that execute after the placement or
connectivity stages, or after a simulation has run.

The hook possesses :guilabel:`postprocess` method, which is the function called in the post-process stage.

**Example of hook structure**

.. code-block:: python

    class MyHook:
        def postprocess(self):
            # instructions for post-processing

AfterPlacementHook
==================

``AfterPlacementHook`` registers a function that runs after the placement step
and before the connectivity step.

:class:`AfterPlacementHook <bsb:bsb.postprocessing.AfterPlacementHook>` is an abstract class, this means
that the :guilabel:`postprocess` method needs to be implemented by the user.

An example of ``AfterPlacementHook`` that allows users to label cells according to their position can be found :doc:`here </examples/label_cells>`



AfterConnectivityHook
=====================

The :class:`AfterConnectivityHook <bsb:bsb.postprocessing.AfterConnectivityHook>`
operates similarly to ``AfterPlacementHook``, but is executed only after
the connectivity stage is complete.

The BSB provides several built-in :doc:`hooks </postprocess/afterconnectivity_list>`.


AfterSimulationHook
===================

The :class:`AfterSimulationHook <bsb:bsb.simulation.postprocessing.AfterSimulationHook>`
runs once a simulation has finished and its results have been collected, which makes it
the place to report on, or further analyse, what a simulation produced.

It is not a workflow stage hook, so it is not configured on the root node: it belongs to
a single simulation, under that simulation's :guilabel:`after_simulation` block. Its
:guilabel:`postprocess` method takes the adapter that ran the simulation, the simulation
itself, and its
:class:`SimulationResult <bsb:bsb.simulation.results.SimulationResult>`:

.. code-block:: python

    from neo import io

    from bsb import AfterSimulationHook, config


    @config.node
    class SpikeReport(AfterSimulationHook):
        path = config.attr(type=str, required=True)

        def postprocess(self, adapter, simulation, result):
            # Only the main node writes the report.
            if adapter.comm.get_rank():
                return
            with open(self.path, "w") as f:
                for train in self.read_block(result).segments[0].spiketrains:
                    print(train.annotations["device"], len(train), file=f)

        def read_block(self, result):
            if not result.filename:
                return result.block
            blocks = io.NixIO(result.filename, "ro").read_all_blocks()
            return next(
                b for b in blocks if b.annotations["nix_name"] == result.block_key
            )

.. warning::

  Results are streamed straight to file whenever an output file is given, which the
  CLI always does. In that case the data never passes through the result object:
  :attr:`result.block <bsb:bsb.simulation.results.SimulationResult.block>` raises, and
  the hook has to read the block back out of ``result.filename``, as above. Only
  results built without a filename, which is what
  :meth:`run_simulation <bsb:bsb.core.Scaffold.run_simulation>` does when it is not
  given one, carry their block in memory.

The hook is configured like any other component:

.. tab-set::

   .. tab-item:: JSON

      .. code-block:: json

          "simulations": {
              "my_simulation": {
                  "after_simulation": {
                      "report": {
                          "strategy": "my_module.SpikeReport",
                          "path": "spikes.txt"
                      }
                  }
              }
          }

   .. tab-item:: Python

      .. code-block:: python

          config.simulations["my_simulation"].after_simulation = dict(
              report=dict(strategy=my_module.SpikeReport, path="spikes.txt")
          )

Every hook runs on every node that took part in the simulation, so a hook that writes
output has to guard itself with ``adapter.comm.get_rank()``, as above. The simulator is
still set up while the hooks run, so backend state can be inspected as well. The network
storage, on the other hand, is no longer read-only, so hooks may write their findings
back to it.

Parallel execution
==================

By default, the placement and connectivity hooks are not parallelized. However,
if there is a need to split the workload across multiple jobs, this can be
implemented in the :guilabel:`queue` method of the hook.

The following example demonstrates how a post-processing task can be divided
into multiple chunks and submitted to a job pool for parallel execution:

.. code-block:: python

   class MyParallelHook(AfterPlacementHook):

       def queue(self, pool):
           def static_function(scaffold, name, chunk=None):
               return scaffold.after_placement[name].postprocess(chunk)

           chunks = np.unique(
               np.concatenate(
                   [p.to_chunks(self.scaffold.network.chunk_size)
                    for p in self.scaffold.partitions.values()]
               ),
               axis=0
           )

           for chunk in chunks:
               pool.queue(
                   static_function,
                   (self.name,),
                   chunk=chunk,
                   submitter=self
               )

       def postprocess(self, chunk):
           # instructions for post-processing
