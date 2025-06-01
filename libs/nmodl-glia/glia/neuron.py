import typing
import weakref

if typing.TYPE_CHECKING:
    from .assets import Mod


class MechAccessor:
    def __init__(self, section, mod: "Mod", point_process=None):
        self._section_name = section.hname()
        self._section = weakref.proxy(section)
        self._mod = mod
        self._pp = point_process
        self._references = []

    def __neuron__(self):
        if self._pp is not None:
            try:
                from patch import transform

                return transform(self._pp)
            except Exception:
                pass
            return self._pp
        else:
            raise TypeError(
                "Density mechanisms can't be retrieved as a standalone Patch/NEURON "
                "entity. "
            )

    def __ref__(self, other):
        self._references.append(other)

    def __deref__(self, other):
        self._references.remove(other)

    @property
    def _connections(self):
        try:
            return self._pp._connections
        except AttributeError:
            raise TypeError(
                "Can't connect Patch/NEURON entities to a density mechanism."
            ) from None

    @_connections.setter
    def _connections(self, value):
        self._pp._connections = value

    def stimulate(self, *args, **kwargs):
        if self._pp is not None:
            return self._pp.stimulate(*args, **kwargs)
        else:
            raise TypeError("Can't stimulate a DensityMechanism.")

    def record(self, param=None, x=0.5):
        from patch import p

        if param is not None and self._pp is None:
            return p.record(
                getattr(self._section(x), f"_ref_{param}_{self._mod.mod_name}")
            )
        else:
            return p.record(self)

    def __record__(self):
        if self._pp is not None:
            return self._pp.__record__()
        else:
            raise TypeError(
                "No default record for DensityMechanisms, use .record('param') instead."
            )

    def set(self, attribute_or_dict, value=None, /, x=None):
        if value is None:
            for k, v in attribute_or_dict.items():
                self.set_parameter(k, v, x)
        else:
            self.set_parameter(attribute_or_dict, value, x)

    def set_parameter(self, param, value, x=None):
        mod = self._mod.mod_name
        if self._pp is not None:
            if param not in self._pp.parameters:
                raise AttributeError(
                    f"Point process {self._mod.mod_name} has no parameter '{param}'"
                )
            return setattr(self._pp, param, value)
        try:
            if x is None:
                setattr(self._section.__neuron__(), f"{param}_{mod}", value)
            else:
                setattr(getattr(self._section(x), mod), value)
        except ReferenceError:
            raise ReferenceError(
                "Trying to set attribute on section"
                f" '{self._section_name}' that has since been garbage collected"
            ) from None

    def get_parameter(self, param, x=None):
        if self._pp is not None:
            return getattr(self._pp, param)
        mod = self._mod.mod_name
        try:
            if x is None:
                return getattr(self._section.__neuron__(), f"{param}_{mod}")
            else:
                return getattr(getattr(self._section(x), mod), param)
        except ReferenceError:
            raise ReferenceError(
                "Trying to set attribute on section"
                f" '{self._section_name}' that has since been garbage collected"
            ) from None
        except AttributeError:
            raise AttributeError(
                f"Parameter '{param}' does not exist on {self._mod.asset_name}"
            ) from None

    @property
    def parameters(self):
        raise NotImplementedError(
            "Parameter overview not implemented yet. Use `get_parameter` instead."
        )
