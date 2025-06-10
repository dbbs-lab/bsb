class Parameter:
    pass


class IonParameter(Parameter):
    def __init__(self, ion: str, prop: str, value: float):
        self._ion = ion
        self._prop = prop
        self._value = value


class MechParameter(Parameter):
    pass


class CableParameter(Parameter):
    def __init__(self, prop: str, value: float):
        self._prop = prop
        self._value = value

    def set_cable_params(self, cable):
        setattr(cable, self._prop, self._value)
