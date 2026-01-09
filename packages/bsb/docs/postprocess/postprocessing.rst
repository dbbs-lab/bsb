###############
Post processing
###############

The BSB allows users to implement and register custom functions that run between
workflow stages to perform additional tasks that are not covered by the
built-in steps.

Users can register postprocessing hooks that execute after either the
placement or connectivity stages.

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


Parallel execution
==================

By default, post-processing hooks are not parallelized. However, if there is
a need to split the workload across multiple jobs, this can be implemented in
the :guilabel:`queue` method of the hook.

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
