###############
Post Processing
###############

The BSB allows users to implement and register custom functions that run between
workflow stages to perform additional tasks that are not covered by the
built-in steps.

Users can register postprocessing hooks that execute after either the
**Placement** or **Connectivity** stages.

The hook possess :guilabel:`postprocess` method, which is the function called in the post-process stage.

**Example of hook structure**

.. code-block:: python

    class MyHook:
        def postprocess(self):
            # instructions for post-processing

AfterPlacementHook
==================

`AfterPlacementHook` registers a function that runs after the placement step
and before the connectivity step.

:class:`AfterPlacementHook <bsb:bsb.postprocessing.AfterPlacementHook>` is an abstract class, this means
that the :guilabel:`postprocess` method need to be implemented.

An example of `AfterPlacementHook` that allow the user to label cells according to their position can be found :doc:`here </examples/label_cells>`



AfterConnectivityHook
=====================

The :class:`AfterConnectivityHook <bsb:bsb.postprocessing.AfterConnectivityHook>`
operates similarly to `AfterPlacementHook`, but is executed **only after
the connectivity stage is complete**.

The BSB provides several built-in :doc:`hooks </postprocess/afterconnectivity_list>`.


Parallel
========

class AfterPlacementHook(abc.ABC):
    name: str = config.attr(key=True)

    def queue(self, pool):
        def static_function(scaffold, name):
            return scaffold.after_placement[name].postprocess()

        chunks = np.unique(
            np.concatenate([p.to_chunks(self.scaffold.network.chunk_size) for p in self.scaffold.partitions]), axis=0
        )
        for chunk in chunks:
            pool.queue(static_function, (self.name,), submitter=self)

    @abc.abstractmethod
    def postprocess(self):  # pragma: nocover
        pass