import glia as g
from patch import p


class Synapse:
    def __init__(
        self,
        cell,
        section,
        point_process_name,
        attributes=None,
        variant=None,
        type=None,
        source=None,
    ):
        if attributes is None:
            attributes = {}

        self._cell = cell
        self._type = type
        self._section = section
        self._point_process_name = point_process_name
        self.source = source
        with g.context(pkg=cell.__class__.glia_package):
            self._point_process_glia_name = g.resolve(point_process_name, variant=variant)
            self._point_process = g.insert(section, point_process_name, variant=variant)
        section.__ref__(self)
        for key, value in attributes.items():
            setattr(self._point_process, key, value)

    def __neuron__(self):
        return self._point_process.__neuron__()

    def stimulate(self, *args, **kwargs):
        return self._point_process.stimulate(*args, **kwargs)

    def record(self):
        return p.record(self._point_process._ref_i)

    def presynaptic(self, section, x=0.5, **kwargs):
        if self.source is None:
            return p.NetCon(section(x)._ref_v, self._point_process, sec=section, **kwargs)
        else:
            setattr(self._point_process, f"_ref_{self.source}", section(x)._ref_v)
