import warnings
from functools import cache, wraps

# We don't need to reraise ImportErrors, they should be clear enough by themselves. If not
# and you're reading this: Fix the NEURON install, it's currently not importable ;)
from neuron import h as _h

from .core import (
    assert_connectable,
    is_nrn_scalar,
    is_point_process,
    is_section,
    is_segment,
    transform,
    transform_netcon,
)
from .error_handler import CatchNetCon, CatchSectionAccess, catch_hoc_error
from .exceptions import (
    BroadcastError,
    HocSectionAccessError,
    ParallelConnectError,
)
from .objects import (
    IClamp,
    NetCon,
    PointProcess,  # noqa: F401  # Function used during metaprogramming
    PythonHocObject,
    SEClamp,
    Section,
    SectionRef,
    VecStim,
    Vector,
    _get_obj_registration_queue,
    _safe_call,
)
from .version import get_neuron_version

_nrnver = get_neuron_version()

try:
    if _nrnver < "7.8":  # pragma: nocover
        raise ImportError("Patch 3.0+ only supports NEURON v7.8.0 or higher.")
except Exception:  # pragma: nocover
    warnings.warn(
        "Could not establish whether Patch supports installed NEURON version "
        f"`{_nrnver}`",
        stacklevel=1,
    )


class TimeSingleton(Vector):
    @cache
    def __new__(cls, *args, **kwargs):
        return super().__new__(cls)


class PythonHocInterpreter:
    __pc: "ParallelContext"
    __point_processes = []
    __h = _h

    def __init__(self):
        self.__loaded_extensions = []
        self.load_file("stdrun.hoc")
        self.celsius = 32
        self._finitialized: bool = False

    @classmethod
    def _process_registration_queue(cls):
        """
        Most PythonHocObject classes (all those provided by Patch for sure) are created
        before the PythonHocInterpreter class is available. Yet they require the class to
        combine the original pointer from ``h.<object>`` (e.g. ``h.Section``) with a
        function that defers to their constructor so that you can call ``p.Section()`` and
        create a PythonHocObject wrapped around the underlying ``h`` pointer.

        This function is called right after the PythonHocInterpreter class is created so
        that PythonHocObjects can place themselves in a queue and have themselves
        registered into the class right after it's ready.
        """
        for hoc_object_class in _get_obj_registration_queue():
            cls.register_hoc_object(hoc_object_class)

    @classmethod
    def register_hoc_object(interpreter_class, hoc_object_class):
        h = interpreter_class.__h

        if hoc_object_class.__name__ in interpreter_class.__dict__:
            # The function call was overridden in the interpreter and should not be
            # destroyed.
            return
        hoc_object_name = hoc_object_class.__name__
        # If the original interpreter doesn't have a function with the same name we can't
        # simplify the constructor of the PythonHocObject and shouldn't wrap it.
        if hasattr(h, hoc_object_name):
            # Wrap it in the interpreter with a call to the underlying `h` to obtain a
            # pointer and use that to make our PythonHocObject
            factory = getattr(h, hoc_object_name)

            @wraps(hoc_object_class.__init__)
            def wrapper(interpreter_instance, *args, **kwargs):
                hoc_ptr = factory(*args, **kwargs)
                return hoc_object_class(interpreter_instance, hoc_ptr)

            setattr(interpreter_class, hoc_object_class.__name__, wrapper)

    def __getattr__(self, attr_name):
        # Get the missing attribute from h
        return getattr(self.__h, attr_name)

    def __setattr__(self, attr, value):
        if hasattr(self.__h, attr):
            setattr(self.__h, attr, value)
        else:
            self.__dict__[attr] = value

    def nrn_load_dll(self, path):
        result = self.__h.nrn_load_dll(path)
        self.__class__._wrap_point_processes()
        return result

    def NetCon(self, source, target, *args, **kwargs):
        nrn_source = transform_netcon(source)
        nrn_target = transform_netcon(target)
        # Change the NetCon signature so that weight, delay and threshold become
        # independent optional keyword arguments.
        setters = {}
        # Set sensible defaults: NetCons appear not to work sometimes if they're not set.
        defaults = {"weight": 0.1, "delay": 1, "threshold": -20}
        setter_keys = ["weight", "delay", "threshold"]
        for key in setter_keys:
            if key not in kwargs:
                kwargs[key] = defaults[key]
            setters[key] = kwargs[key]
            del kwargs[key]
        if is_section(source):
            kwargs["sec"] = source
        elif is_segment(source):
            kwargs["sec"] = source.sec
        elif is_nrn_scalar(source) and "sec" not in kwargs:
            raise ConnectionError(
                "Using NetCon with a scalar such as s(0.5)._ref_v is discouraged. "
                "Use s(0.5) instead."
            )
        if "sec" in kwargs:
            kwargs["sec"] = transform(kwargs["sec"])
        # Execute HOC NetCon and wrap result into `connection`
        with catch_hoc_error(CatchNetCon, nrn_source=nrn_source, nrn_target=nrn_target):
            connection = NetCon(
                self,
                self.__h.NetCon(nrn_source, nrn_target, *args, **kwargs),
            )
        # Set the weight, delay and threshold independently
        for k, v in setters.items():
            if k == "weight":
                if hasattr(type(v), "__iter__"):  # pragma: nocover
                    for i, w in enumerate(v):
                        connection.weight[i] = w
                else:
                    connection.weight[0] = v
            else:
                setattr(connection, k, v)
        # Have the NetCon reference source and target
        connection.__ref__(source)
        connection.__ref__(target)
        # If target is None, this NetCon is used as a spike detector.
        if target is not None:
            # Connect source and target.
            assert_connectable(source, label="Source")
            assert_connectable(target, label="Target")
            source._connections[target] = connection
            target._connections[source] = connection
        elif hasattr(source, "__ref__"):
            # Since the connection isn't established, make sure that the source and NetCon
            # reference each other both ways
            source.__ref__(connection)

        return connection

    def ParallelCon(self, a, b, output=True, *args, **kwargs):
        a_int = isinstance(a, int)
        b_int = isinstance(b, int)
        gid = a if a_int else b
        if a_int != b_int:
            if b_int:
                source = a
                nc = self.NetCon(source, None, *args, **kwargs)
                self.parallel.set_gid2node(gid, self.parallel.id())
                self.parallel.cell(gid, nc)
                if output:
                    self.parallel.outputcell(gid)
                # We only set threshold for sending NetCon's, as setting it on receiving
                # NetCons may break transmission:
                # https://github.com/neuronsimulator/nrn/issues/2135
                nc.threshold = kwargs.get("threshold", -20.0)
            else:
                target = b
                nc = self.parallel.gid_connect(gid, target)
                nc.delay = kwargs.get("delay", nc.delay)
                nc.weight[0] = kwargs.get("weight", nc.weight[0])
            nc.gid = gid
            return nc
        else:
            raise ParallelConnectError(
                "Either the first or second argument has to be an integer GID."
            )

    def SectionRef(self, *args, sec=None):
        if len(args) > 1:
            raise TypeError(
                f"SectionRef takes 1 positional argument but {len(args)} given."
            )
        if sec is None:
            if args:
                sec = args[0]
            else:
                sec = self.cas()
                if not sec:  # pragma: nocover
                    raise RuntimeError(
                        "SectionRef() failed as there is no currently accessed section "
                        "available. Please specify a Section."
                    )
        ref = SectionRef(self, self.__h.SectionRef(sec=transform(sec)))
        if transform(sec) is sec:
            sec = Section(self, sec)
        ref.__ref__(sec)
        ref.__dict__["sec"] = sec
        ref.section = sec
        return ref

    def ParallelContext(self):
        return self.parallel

    def VecStim(self, /, *args, pattern=None, **kwargs):
        import glia as g

        mod_name = g.resolve("VecStim")
        vec_stim = VecStim(self, getattr(self.__h, mod_name)(*args, **kwargs))
        if pattern is not None:
            pattern_vector = self.Vector(pattern)
            vec_stim.play(pattern_vector.__neuron__())
            self._vector = pattern_vector
            self._pattern = pattern
        return vec_stim

    def IClamp(self, x=0.5, sec=None):
        sec = sec if sec is not None else self.cas()
        clamp = IClamp(self, self.__h.IClamp(x, sec=transform(sec)))
        clamp.__ref__(sec)
        if hasattr(sec, "__ref__"):
            sec.__ref__(clamp)
        return clamp

    def SEClamp(self, sec, x=0.5):
        clamp = SEClamp(self, self.__h.SEClamp(transform(sec(x))))
        clamp.__ref__(sec)
        if hasattr(sec, "__ref__"):
            sec.__ref__(clamp)
        return clamp

    @property
    def time(self):
        # Fix for upstream NEURON bug. See https://github.com/neuronsimulator/nrn/issues/416
        if not any(self.allsec()):  # pragma: nocover
            self.__dud_section = self.Section(name="this_is_here_to_record_time")
        # Time vectors need to be shared, because it can only be recorded into 1
        # target, but should also update every time they are accessed, to resize them
        # between simulation sessions
        time_singleton = TimeSingleton(self, self.__h.Vector().record(self._ref_t))
        return time_singleton

    def finitialize(self, initial=None):
        self.parallel.set_maxstep(10)
        self._setup_transfer()
        if initial is not None:
            self.__h.finitialize(initial)
        else:
            self.__h.finitialize()
        self._finitialized = True

    def continuerun(self, duration, v_init=None):
        self._do_init(v_init)
        self.parallel.psolve(self.__h.t + duration, v_init)

    def run(self, duration, v_init=None, reset=True):
        self._do_init(v_init, reset=reset)
        self.__h.continuerun(duration)

    def _do_init(self, v_init=None, reset=False):
        if reset or not self._finitialized:
            self.finitialize(v_init)

    def cas(self):
        # Currently error won't be triggered as h.cas() exits on undefined section acces:
        # https://github.com/neuronsimulator/nrn/issues/769
        try:
            with catch_hoc_error(CatchSectionAccess):
                return Section(self, self.__h.cas())
        except HocSectionAccessError:  # pragma: nocover
            return None

    def _init_pc(self):
        if not hasattr(self, "_PythonHocInterpreter__pc"):
            pc = ParallelContext(self, self.__h.ParallelContext())
            try:
                from mpi4py import MPI
            except Exception:
                self.__h.nrnmpi_init()
                msize = pc.nhost()
            else:
                msize = MPI.COMM_WORLD.size

            hosts = pc.nhost()
            if msize != hosts:  # pragma: nocover
                raise RuntimeError(
                    f"MPI initialization error. `mpi4py` has a universe of size {msize},"
                    + f" while NEURON has {hosts} hosts. Make sure that you import"
                    + " `mpi4py` before importing either NEURON or Patch. If you did so,"
                    + " your tools must not agree on which MPI implementation to use."
                )
            self.__pc = pc

    @property
    def parallel(self) -> "ParallelContext":
        self._init_pc()
        return self.__pc

    def record(self, target):
        v = self.Vector()
        v.record(target)
        return v

    @classmethod
    def _wrap_point_processes(cls):
        # Filter out all the point processes in the interpreter
        point_processes = [k for k in dir(cls.__h) if is_point_process(k)]
        old_point_processes = cls.__point_processes
        # Check if there are any new things to wrap.
        for point_process in set(point_processes) - set(old_point_processes):
            # For each point process check if a function already exists, if not, wrap the
            # HocInterpreter factory function.
            if point_process not in cls.__dict__:
                setattr(cls, point_process, cls._wrap_point_process(point_process))
        cls.__point_processes = point_processes

    @classmethod
    def _wrap_point_process(cls, point_process):
        # Create a function that has the right `f.__code__.co_name` for error messages.
        scope = {}
        exec(
            f"""def {point_process}(self, target, *args, **kwargs):
            h = getattr(self, '_PythonHocInterpreter__h')
            factory = getattr(h, '{point_process}')
            og_target = target
            if hasattr(target, "__arc__"):
                target = target(target.__arc__(), ephemeral=True)
            nrn_target = transform(target)
            nrn_ptr = factory(nrn_target, *args, **kwargs)
            point_process = PointProcess(self, nrn_ptr)
            if hasattr(og_target, "__ref__"):
                og_target.__ref__(point_process)
            point_process.__ref__(og_target)
            return point_process""",
            globals(),
            scope,
        )

        return scope[point_process]

    def _setup_transfer(self):  # pragma: nocover
        v = self.__h.Vector()
        self.parallel.allgather(self.parallel._transfer_flag, v)
        should_setup = sum(v)
        if should_setup:
            self.parallel.setup_transfer()


class ParallelContext(PythonHocObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._warn_new_gids = False
        self._transfer_max = -1
        self._transfer_flag = False

    def cell(self, gid, nc):
        transform(self).cell(gid, transform(nc))

    def set_gid2node(self, gid, id=None):
        if self._warn_new_gids:
            warnings.warn(
                f"New GID ({gid}) registered after `spike_record` was called."
                " This GID will not be recorded.",
                stacklevel=2,
            )
        if id is None:
            id = self.id()
        return transform(self).set_gid2node(gid, id)

    def gid_connect(self, gid, target):
        nrn_nc = transform(self).gid_connect(gid, transform_netcon(target))
        nc = NetCon(self, nrn_nc)
        # Forbid set threshold. See https://github.com/neuronsimulator/nrn/issues/2135
        nc._nothreshold = True
        nc.__ref__(target)
        if hasattr(target, "__ref__"):
            target.__ref__(nc)
        return nc

    @_safe_call
    def source_var(self, call_result, *args, **kwargs):  # pragma: nocover
        key = args[-1]
        if key < 0:
            raise ValueError("Transfer variable keys must be larger than 0.")
        # Store the highest used identifier
        self._transfer_max = max(self._transfer_max, args[-1])
        self._transfer_flag = True
        return call_result

    @_safe_call
    def target_var(self, call_result, *args, **kwargs):  # pragma: nocover
        key = args[-1]
        if key < 0:
            raise ValueError("Transfer variable keys must be larger than 0.")
        # Store the highest used identifier
        self._transfer_max = max(self._transfer_max, args[-1])
        self._transfer_flag = True
        return call_result

    @_safe_call
    def setup_transfer(self, call_result, *args, **kwargs):  # pragma: nocover
        self._transfer_flag = False
        return call_result

    def spike_record(self, gids=-1, time_vector=None, gid_vector=None, /):
        if time_vector is None:
            time_vector = self._interpreter.Vector()
        if gid_vector is None:
            gid_vector = self._interpreter.Vector()
        transform(self).spike_record(gids, transform(time_vector), transform(gid_vector))
        if gids == -1:
            self._warn_new_gids = True
        return time_vector, gid_vector

    def broadcast(self, data, root=0):
        """
        Broadcast either a Vector or arbitrary picklable data. If ``data`` is a Vector,
        the Vectors are resized and filled with the data from the Vector in the ``root``
        node. If ``data`` is not a Vector, it is pickled, transmitted and returned from
        this function to all nodes.

        :param data: The data to broadcast to the nodes.
        :type data: :class:`Vector <.objects.Vector>` or any picklable object.
        :param root: The id of the node that is broadcasting the data.
        :type root: int
        :returns: None (Vectors filled) or the transmitted data
        :raises: BroadcastError if ``neuron.hoc.HocObjects`` that aren't Vectors are
          transmitted
        """
        import neuron

        data_ptr = transform(data)
        # Is anyone broadcasting a HocObject?
        if isinstance(data_ptr, neuron.hoc.HocObject):
            # Comparing dir is used as a silly equality check because all NEURON object
            # have class 'neuron.hoc.HocObject'
            if dir(data_ptr) == dir(neuron.h.Vector()):
                # If this node is broadcasting a Vector, then proceed to traditional
                # broadcasting. If all nodes are broadcasting a Vector traditional
                # broadcasting will occur, otherwise a BroadcastError is thrown.
                transform(self).broadcast(data_ptr, root)
                # After succesful broadcasts, the Vector is updated, return it.
                return data
            else:
                # Send an empty vector so the other nodes don't hang.
                transform(self).broadcast(transform(self._interpreter.Vector()), root)
                raise BroadcastError(
                    "NEURON HocObjects cannot be broadcasted, "
                    "they need to be created on their own nodes."
                )
        else:
            # If noone is sending a HocObject we proceed with picklable data broadcasting
            return self._broadcast(data, root=root)

    def _broadcast(self, data, root=0):
        import pickle

        if self.id() == root:
            try:
                v = self._interpreter.Vector(list(pickle.dumps(data)))
            except Exception as e:
                # Send an empty vector
                # so the other nodes don't hang waiting for a broadcast.
                transform(self).broadcast(transform(self._interpreter.Vector()), root)
                raise BroadcastError(str(e)) from None
        else:
            v = self._interpreter.Vector()
        v = transform(v)
        transform(self).broadcast(v, root)
        try:
            return pickle.loads(bytes([int(d) for d in v]))
        except EOFError:
            raise BroadcastError(
                "Root node did not transmit. Look for root node error."
            ) from None

    def psolve(self, tstop, v_init=None):
        self_ = transform(self)
        self_.set_maxstep(10)
        self._interpreter._do_init(v_init)
        self_.psolve(tstop)


PythonHocInterpreter._process_registration_queue()
PythonHocInterpreter._wrap_point_processes()
