from bsb import DeviceModel, Targetting, config


@config.dynamic(attr_name="device", auto_classmap=True)
class NeuronDevice(DeviceModel):
    targetting = config.attr(type=Targetting, required=True)
