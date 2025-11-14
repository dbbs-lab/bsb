import typing
from collections.abc import Sequence

from .core import _is_sequence, transform, transform_record
from .error_handler import CatchRecord, catch_hoc_error

if typing.TYPE_CHECKING:  # pragma: nocover
    from .interpreter import PythonHocInterpreter


_registration_queue = []
_had_pointers_wrapped = {}


def _safe_call(method):
    """
    Internal decorator to defer a method to the underlying NEURON object, unpacking all
    args and returning the result to the decorated method.
    """

    def caller(self, *args, **kwargs):
        call_result = self._safe_call(method.__name__, *args, **kwargs)
        return method(self, call_result, *args, **kwargs)

    return caller


class PythonHocObject:
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        try:
            from .interpreter import PythonHocInterpreter
        except ImportError:
            _registration_queue.append(cls)
            return

        PythonHocInterpreter.register_hoc_object(cls)

    def __init__(self, interpreter: "PythonHocInterpreter", ptr):
        # Initialize ourselves with a reference to our own "pointer"
        # and prepare a list for other references.
        self._neuron_ptr = transform(ptr)
        self._references = []
        self._interpreter = interpreter
        super().__init__()

    def __getattr__(self, attr):
        # Return underlying attributes that aren't explicitly set on the wrapper
        return getattr(self.__dict__["_neuron_ptr"], attr)

    def __setattr__(self, attr, value):
        # Check if we're shadowing a class attribute (like properties).
        if getattr(type(self), attr, None) is not None:
            return super().__setattr__(attr, value)
        # Set attributes on the underlying pointer, and set on self if they don't
        # exist on the underlying pointer. This allows you to set arbitrary values
        # on the NEURON objects as you would be able to with a real Pythonic object.
        try:
            setattr(self._neuron_ptr, attr, value)
        except (LookupError, AttributeError) as _:
            self.__dict__[attr] = value

    def __call__(self, *args, **kwargs):
        # Relay calls to self to the underlying pointer
        return self._neuron_ptr(*args, **kwargs)

    def __iter__(self):
        # Create an iterator from ourselves.
        ptr = self.__neuron__()
        if type(ptr).__name__ == "Section":
            # Iter on section isn't a full iterator.
            return ptr
        # Relay iteration to the underlying pointer
        try:
            return iter(ptr)
        except TypeError:
            raise

    def __bool__(self):
        return True

    def __len__(self):
        # Relay length to pointer
        return len(self.__neuron__())

    def __eq__(self, other):
        return transform(self) is transform(other)

    def __repr__(self):
        ostr = object.__repr__(self)
        return ostr[: ostr.rindex("at")] + "pointing to '" + str(self.__neuron__()) + "'>"

    def __dir__(self) -> typing.Iterable[str]:
        return sorted(set(dir(transform(self))) | set(super().__dir__()))

    def __hash__(self):
        return object.__hash__(self)

    def __neuron__(self):
        """
        Magic method that is called when this object is passed to NEURON.
        """
        return self._neuron_ptr

    def __ref__(self, obj):
        """
        Magic method that is called when a strong reference needs to be stored on the
        object.
        """
        if obj not in self._references:
            self._references.append(obj)

    def __deref__(self, obj):
        """
        Magic method that is called when a strong reference needs to be removed from the
        object.
        """
        try:
            self._references.remove(obj)
            return True
        except ValueError:
            return False

    def _safe_call(self, func_name, *args, **kwargs):
        """
        Unpacks all arguments to their NEURON variant and retrieves the naked function
        from the HocObject then calls it.
        """
        func = getattr(transform(self), func_name)
        args = [transform(a) for a in args]
        kwargs = {k: transform(v) for k, v in kwargs.items()}
        return func(*args, **kwargs)


class Connectable:
    def __init__(self, *args, **kwargs):
        # Prepare a dictionary that lists which other NEURON parts this is connected to
        self._connections = {}
        super().__init__(*args, **kwargs)


class PointerWrapper:
    def __init__(self, attr):
        self._attr = attr

    def __get__(self, instance, owner):
        if instance is None:
            return self

        value = getattr(instance.__neuron__(), self._attr)
        t = instance._interpreter.t

        class SimulationValue(type(value)):
            def __record__(v):
                return getattr(instance.__neuron__(), f"_ref_{self._attr}")

            def __str__(v):
                return str(type(value)(v))

            def __repr__(v):
                return f"<{self._attr}={value} at t={t} of {instance}>"

        return SimulationValue(value)

    def __set__(self, instance, value):
        setattr(instance.__neuron__(), self._attr, value)


class WrapsPointers:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._init_pointers_wrappers()

    def _init_pointers_wrappers(self):
        cls = type(self)
        target = self.__neuron__()
        hoctype = str(target).split("[")[0].split("_0x")[0]
        if hoctype not in _had_pointers_wrapped:
            params = []
            for k in dir(target):
                if not k.startswith("_"):
                    try:
                        ptr_str = str(getattr(target, f"_ref_{k}", None))
                        is_ptr = ptr_str.startswith("<pointer") or ptr_str.startswith(
                            "data_handle"
                        )
                    except Exception:
                        is_ptr = False
                    if is_ptr:
                        setattr(cls, k, PointerWrapper(k))
                        params.append(k)
            _had_pointers_wrapped[hoctype] = params
        self.parameters = _had_pointers_wrapped[hoctype]


class Section(PythonHocObject, Connectable, WrapsPointers):
    def connect(self, target, *args, **kwargs):
        """
        Connect this section to another one as child section.
        """
        nrn_target = transform(target)
        self.__neuron__().connect(nrn_target, *args, **kwargs)
        if hasattr(target, "__ref__"):
            target.__ref__(self)
        self.__ref__(target)

    @property
    def parent(self):
        """
        Returns the parent of the Section, or ``None``
        """
        ref = self._interpreter.SectionRef(sec=self)
        return Section(self._interpreter, ref.parent) if ref.has_parent() else None

    def __arc__(self):
        """
        Return the default arc-position (a point in the closed interval [0, 1] that
        represents the position between start and end of the Section).

        Defaults to 0.5
        """
        return 0.5

    def __netcon__(self):
        """
        Return the default pointer to connect to a NetCon.

        Defaults to ``self(0.5)._ref_v``
        """
        return self(self.__arc__()).__netcon__()

    def __record__(self):
        """
        Return the default pointer to record.

        Defaults to ``self(0.5)._ref_v``
        """
        return self(self.__arc__()).__record__()

    def __call__(self, x, ephemeral=False, *args, **kwargs):
        v = super().__call__(x, *args, **kwargs)
        if type(v).__name__ != "Segment":  # pragma: nocover
            raise TypeError("Section call did not return a Segment.")
        seg = Segment(self._interpreter, v, self)
        if not ephemeral:
            # By default store references to segments, but allow for them to be
            # garbage collected if `ephemeral=True`
            seg.__ref__(self)
            self.__ref__(seg)
        return seg

    def __iter__(self, *args, **kwargs):
        iter = super().__iter__(*args, **kwargs)
        for v in iter:
            if type(v).__name__ != "Segment":  # pragma: nocover
                raise TypeError("Section iteration did not return a Segment.")
            yield Segment(self._interpreter, v, self)

    def insert(self, *args, **kwargs):
        """
        Insert a mechanism into the Section.
        """
        # Catch nrn.Section return value, always seems to be self.
        # So if Neuron doesn't raise an error, return self.
        # Probably for method chaining?
        self.__neuron__().insert(*args, **kwargs)
        return self

    def connect_synapse(self, target, **kwargs):
        """
        Connect a Segment of this Section to a target.

        Usually used to connect the membrane potential to a point process.
        """
        return self._interpreter.NetCon(self, target, **kwargs)

    def set_dimensions(self, length, diameter):
        """
        Set the length and diameter of the piece of cable this Section will represent in
        the simulation.
        """
        self.L = length
        self.diam = diameter

    def set_segments(self, segments):
        """
        Set the number of discrete points where equations are solved during simulation.
        """
        self.nseg = segments

    def add_3d(self, points, diameters=None):
        """
        Add new 3D points to this section xyz data.

        :param points: A 2D array of xyz points.
        :param diameters: A scalar or array of diameters corresponding to the points.
            Default value is the section diameter.

        :type diameters: float | list[float]
        """
        if diameters is None:
            diameters = [self.diam for _ in range(len(points))]
        if not _is_sequence(diameters):
            diameters = [diameters for _ in range(len(points))]
        self.__neuron__().push()
        for point, diameter in zip(points, diameters, strict=False):
            self._interpreter.pt3dadd(*point, diameter)
        self._interpreter.pop_section()

    @property
    def points(self):
        """
        Return the 3d point information associated to this section.
        """
        import numpy

        return numpy.column_stack(
            (
                [self.x3d(n) for n in range(self.n3d())],
                [self.y3d(n) for n in range(self.n3d())],
                [self.z3d(n) for n in range(self.n3d())],
            )
        )

    def wholetree(self):
        """
        Return the whole tree of child Sections.

        :rtype: List[patch.objects.Section]
        """
        return [Section(self._interpreter, s) for s in self.__neuron__().wholetree()]

    def record(self, x=None):
        """
        Record the Section at a certain point.

        :param x: Arcpoint, defaults to ``__arc__`` if omitted.
        :type x: float
        """
        if x is None:
            x = self.__arc__()
        if not hasattr(self, "recordings"):
            self.recordings = {}
        if x not in self.recordings:
            recorder = self._interpreter.Vector()
            recorder.record(self(x))
            self.recordings[x] = recorder
            return recorder
        return self.recordings[x]

    def synapse(self, factory, *args, store=False, attributes=None, **kwargs):
        """
        Insert a synapse into the Section.

        :param factory: Callable that creates a point process, is given the
          Section as first argument and passes on all other args.
        :type factory: Callable
        :param store: Store the synapse on the Section in a ``synapses``
          attribute.
        :type store: bool
        """
        synapse = factory(self, *args, **kwargs)
        if attributes:
            _syn = transform(synapse)
            for k, v in attributes.items():
                setattr(_syn, k, v)

        if store:
            if not hasattr(self, "synapses"):
                self.synapses = []
            self.synapses.append(synapse)
        return synapse

    def iclamp(
        self,
        amplitude: float = 1,
        *,
        x: float = 0.5,
        delay: float = 0,
        duration: float = 100,
    ) -> "IClamp":
        """
        Create a current clamp on the section.

        :param x: Location along the segment from 0 to 1.
        :type x: float
        :param delay: Duration of the pre-step holding interval, from `0` to `delay` ms.
        :type delay: float
        :param duration: Duration of the step interval,
         from `delay` to `delay + duration` ms.
        :type duration: float
        :param amplitude: Can be a single value to define the current during the step
          (`delay` to `delay + duration` ms), or a sequence to play after `delay` ms. This
          will play 1 value of the sequence into the clamp per timestep.
        :type amplitude: float | list[float]
        :returns: The current clamp placed in the section.
        :rtype: :class:`.objects.SEClamp`
        """
        clamp = self._interpreter.IClamp(x=x, sec=self)
        clamp.delay = delay
        clamp.duration = duration
        clamp.amplitude = amplitude
        return clamp

    def vclamp(
        self,
        voltage: float = -70,
        *,
        x: float = 0.5,
        before: float = 0,
        duration: float = 100,
        after: float = 0,
        holding=-70,
    ) -> "SEClamp":
        """
        Create a voltage clamp on the section.

        :param x: Location along the segment from 0 to 1.
        :type x: float
        :param before: Duration of the pre-step holding interval, from `0` to `delay` ms.
        :type before: float
        :param duration: Duration of the step interval, from `delay` to `delay +
         duration` ms.

        :type duration: float
        :param after: Duration of the post-step holding interval, from `delay + duration`
          to `delay + duration + after` ms.

        :type after: float
        :param voltage: Can be a single value to define the voltage during the step
          (`delay` to `delay + duration` ms), or 3 values to define the pre-step, step and
          post-step voltages altogether.

        :type voltage: float | list[float]
        :param holding: If `voltage` is a single value, `holding` is used for the pre-step
          and post-step voltages.

        :type holding: float
        :returns: The single electrode voltage clamp placed in the section.
        :rtype: :class:`.objects.SEClamp`
        """
        clamp = self._interpreter.SEClamp(x=x, sec=self)
        clamp._holding = holding
        clamp.delay = before
        clamp.duration = duration
        clamp.after = after
        clamp.voltage = voltage
        return clamp

    def push(self):
        """
        Return a context manager that pushes this Section onto the section stack and takes
        it off when the context is exited.
        """
        transform(self).push()

        return _SectionStackContextManager(self)

    def pop(self):
        """
        Pop this section off the section stack.
        """
        if self == self._interpreter.cas():
            self._interpreter.pop_section()
        else:
            raise RuntimeError(
                "Cannot pop this section as it is not on top of the section stack"
            )


class _SectionStackContextManager:
    def __init__(self, section):
        self._section = section

    def __enter__(self):
        pass

    def __exit__(self, *args):
        self._section.pop()


class SectionRef(PythonHocObject):
    @property
    def child(self):
        return [Section(self._interpreter, s) for s in self.__neuron__().child]


class Vector(PythonHocObject):
    def record(self, target, *args, **kwargs):
        nrn_target = transform_record(target)
        with catch_hoc_error(CatchRecord, target=target):
            self.__neuron__().record(nrn_target, *args, **kwargs)
        self.__ref__(target)
        return self


class IClamp(PythonHocObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay: float = 0
        self.dur: float = 1e200
        self.amp: float = 1

    @property
    def duration(self) -> float:
        """
        Get the duration of the current injection.
        """
        return self.dur

    @duration.setter
    def duration(self, duration: float):
        """
        Set the duration of the current injection.

        :param duration: Duration in milliseconds.
        :type duration: float
        """
        self.dur = duration

    @property
    def amplitude(self) -> float:
        """
        Get the amplitude during current injection.
        """
        return self.amp

    @amplitude.setter
    def amplitude(self, amplitude: float | Sequence[float]):
        """
        Set the amplitude during current injection.

        :param amplitude: Can be a single value to define the current during the step
          (`delay` to `delay + duration` ms), or a sequence to play after `delay` ms. This
          will play 1 value of the sequence into the clamp per timestep.
        :type amplitude: float | list[float]
        """
        if _is_sequence(amplitude):
            # If its a sequence play it as a vector into the clamp
            dt = self._interpreter.dt
            t = self._interpreter.Vector(
                [self.delay + dt * i for i in range(len(amplitude))]
            )
            v = self._interpreter.Vector(amplitude, t)
            v.play(self._ref_amp, t.__neuron__())
            self.__ref__(v)
            self.__ref__(t)
        else:
            self.amp = amplitude


class SEClamp(PythonHocObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dur1 = 100
        self.dur2 = 100
        self.dur3 = 100
        self.amp1 = -70
        self.amp2 = -50
        self.amp3 = -70

    def __record__(self):
        return self._ref_i

    @property
    def delay(self):
        """
        Get the delay period from 0ms to `delay` ms during which the holding potential is
        clamped.
        """
        return self.dur1

    @delay.setter
    def delay(self, delay):
        """
        Set the delay period from 0ms to `delay` ms during which the holding potential is
        clamped.

        :param delay: Duration of the pre-step holding interval, from `0` to `delay` ms.
        :type delay: float
        """
        self.dur1 = delay

    @property
    def duration(self):
        """
        Get the duration of the command potential clamping period.
        """
        return self.dur2

    @duration.setter
    def duration(self, duration):
        """
        Set the duration of the command potential clamping period.

        :param duration: Duration of the step interval,
         from `delay` to `delay + duration` ms.
        :type duration: float
        """
        self.dur2 = duration

    @property
    def after(self):
        """
        Get the duration of the period after clamping during which the holding potential
        is clamped.
        """
        return self.dur3

    @after.setter
    def after(self, after):
        """
        Set the duration of the period after clamping during which the holding potential
        is clamped.

        :param after: Duration of the post-step holding interval, from `delay + duration`
            to `delay + duration + after` ms.
        :type after: float
        """
        self.dur3 = after

    @property
    def voltage(self):
        return [self.amp1, self.amp2, self.amp3]

    @voltage.setter
    def voltage(self, voltage):
        """
        Set the control potentials.

        :param voltage: Can be a single value to define the voltage during the step
          (`delay` to `delay + duration` ms), or 3 values to define the pre-step, step and
          post-step voltages altogether.
        :type voltage: float | list[float]
        """
        try:
            voltage = iter(voltage)
        except TypeError:
            self.amp1 = self.holding
            self.amp2 = voltage
            self.amp3 = self.holding
        else:
            voltage = list(voltage)
            self.amp1 = voltage[0]
            self.amp2 = voltage[1]
            self.amp3 = voltage[2]

    @property
    def holding(self):
        """
        Get the holding potential that is active before and after the step period.
        """
        return getattr(self, "_holding", -70)

    @holding.setter
    def holding(self, holding):
        """
        Set the holding potential which is active before and after the step period.

        :param holding: Holding potential
        :type holding: float
        """
        self._holding = holding
        self.amp1 = holding
        self.amp3 = holding


class NetStim(PythonHocObject, Connectable):
    pass


class VecStim(PythonHocObject, Connectable):
    @property
    def vector(self):
        return self._vector

    @property
    def pattern(self):
        return self._pattern.copy()


class NetCon(PythonHocObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._nothreshold = False

    def record(self, vector=None):
        if vector is not None:
            self._neuron_ptr.record(transform(vector))
            self.recorder = vector
            if hasattr(vector, "__ref__"):
                vector.__ref__(self)
        else:
            if not hasattr(self, "recorder"):
                vector = self._interpreter.Vector()
                self._neuron_ptr.record(transform(vector))
                self.recorder = vector
                if hasattr(vector, "__ref__"):
                    vector.__ref__(self)
            return self.recorder

    @property
    def threshold(self):
        return transform(self).threshold

    @threshold.setter
    def threshold(self, value):
        if self._nothreshold:
            raise RuntimeError(
                "Do not set threshold on `gid_connect`ed NetCon's. See "
                "https://github.com/neuronsimulator/nrn/issues/2135 for more information."
            )
        else:
            transform(self).threshold = value


class Segment(PythonHocObject, Connectable, WrapsPointers):
    def __init__(self, interpreter, ptr, section, **kwargs):
        super().__init__(interpreter, ptr, **kwargs)
        self.section = section

    def __netcon__(self):
        return self.__neuron__()._ref_v

    def __record__(self):
        return self.__neuron__()._ref_v

    def __iter__(self):
        # Fix segmentation fault when iterating over segment without mechs.
        # See: https://github.com/neuronsimulator/nrn/issues/3458
        if not self.section.psection()["density_mechs"]:
            return iter(())
        else:
            return super().__iter__()


class PointProcess(PythonHocObject, Connectable, WrapsPointers):
    """
    Wrapper for all point processes (membrane and synapse mechanisms).
    """

    def stimulate(self, pattern=None, weight=0.04, delay=0.0, **kwargs):
        """
        Stimulate a point process.

        :param pattern: Specific stimulus event times to play into the point process.
        :type pattern: list[float]
        :param kwargs: All keyword arguments will be passed set on the
          :class:`NetStim <neuron:NetStim>`
        """

        if pattern is None:
            # No specific pattern given, create NetStim
            stimulus = self._interpreter.NetStim()
            for kw, value in kwargs.items():
                setattr(stimulus.__neuron__(), kw, value)
        else:
            # Specific pattern required, create VecStim
            stimulus = self._interpreter.VecStim(pattern=pattern)
        self._interpreter.NetCon(stimulus, self, weight=weight, delay=delay)
        return stimulus

    def __record__(self):
        return self.__neuron__()._ref_i


def _get_obj_registration_queue():
    return _registration_queue
