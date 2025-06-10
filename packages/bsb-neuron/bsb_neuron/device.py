from bsb import DeviceModel, Targetting, config


@config.dynamic(attr_name="device", auto_classmap=True)
class NeuronDevice(DeviceModel):
    """
    Class representing a NEURON device model.
    """

    device: str
    """The device strategy name."""

    targetting = config.attr(type=Targetting, required=True)
    """Targets of the device."""
