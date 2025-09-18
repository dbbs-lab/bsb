######################
Simulation Controllers
######################

The Brain Scaffold Builder (BSB) allows you to define and trigger actions at specific checkpoints during a simulation.
This is useful for tasks such as resetting values, saving data, or updating a component's state.
You can apply this feature to any SimulationComponent (including ``cell_model``, ``connection_model`` and ``device``) by implementing a Controller.

A Controller is a component that must implement two primary methods:

  * ``get_next_checkpoint()``: This method returns a *float* representing the time of the next checkpoint. The simulation adapter calls this to determine when the controller's progress method should be triggered.

  * ``progress()``: This method contains the logic for the action to be performed when the checkpoint is reached.

An optional third method, ``on_start()``, can also be implemented to trigger an action at the beginning of the simulation.

Example: A simple controlling Device
------------------------------------

This example demonstrates how to extend a custom Device named :guilabel:`MyDevice` to act as a controller.
This controller updates a :guilabel:`status` attribute and prints the value of :guilabel:`ids` attribute every fixed time step.

.. code-block:: python

    @config.node
    class NewController(
        MyDevice
    ):
        step = config.attr(type=float, required=True)

        def __init__(self, **kwargs):
            super().__init__()
            self.status = 0

        def get_next_checkpoint(self):
            return self.status + self.step

        def progress(self):
            self.status += self.step
            print(self.ids)



