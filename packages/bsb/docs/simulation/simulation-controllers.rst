######################
Simulation Controllers
######################

Sometimes can be useful to stop the simulation at a certain checkpoint and trigger an action: could it be to reset a
value or to save data. Here it is possible to make use of this feature with the controllers system:
in practice the BSB will allow you to customize a SimulationComponent, either Cell, Connection od Device, to trigger an action at
defined checkpoints.

A controller is a Component that present two methods:

 * get_next_checkpoint , method that will be called to ask the controller at what time will be its next checkpoint. It should return a *float* .
 * progress, method where to implement the action to trigger when the checkpoint is reached.

optionally it could be implemented a method called on_start if is desired to trigger an action before the simulation starts.

Example to extend a device MyDevice to be a controller that every fixed step will update status attribute and print it:

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

        def progress(self, kwargs=None):
            self.status += self.step
            print(self.status)

.. note:
    The progress method needs kwargs in the arguments, in default adapters it will receive as keyword arguments:
    * simulations= list of Simulation objects that are run
    * simdata= all the SimulationData stored

