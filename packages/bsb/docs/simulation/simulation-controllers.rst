######################
Simulation Controllers
######################

The Brain Scaffold Builder (BSB) allows you to define and trigger actions at specific checkpoints during a simulation.
This is useful for tasks such as resetting values, saving data, or updating a component's state.
You can apply this feature to any SimulationComponent (including ``cell_model``, ``connection_model`` and ``device``) by
implementing the "controller" interface.

A controller is a component that must implement two primary methods:

  * ``get_next_checkpoint()``: This method returns a *float* representing the time of the next checkpoint. The simulation adapter calls this to determine when the simulation will pause next to run a checkpoint.

  * ``run_checkpoint()``: This method contains the logic for the action to be performed when the checkpoint is reached.


Example: A simple controlling Device
------------------------------------

This example demonstrates how to create a controller named :guilabel:`NewController` that updates
the :guilabel:`status` attribute and outputs its value at every fixed time step.

.. code-block:: python

    @config.node
    class NewController:
        step = config.attr(type=float, required=True)

        def __init__(self):
            super().__init__()
            self.status = 0

        def get_next_checkpoint(self):
        # Here insert the logic to determine the timing of your next checkpoint
            return self.status + self.step

        def run_checkpoint(self):
        # The checkpoint is reached, execute all the desired actions
            self.status += self.step
            print("Checkpoint reached!", self.status)



