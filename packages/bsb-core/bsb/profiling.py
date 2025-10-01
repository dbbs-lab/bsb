import atexit
import cProfile
import functools
import importlib.metadata
import inspect
import json
import pickle
import sys
import warnings
from functools import cache
from uuid import uuid4

from opentelemetry import trace

from .services import MPI


class ProfilingSession:
    def __init__(self):
        self._started = False
        self.name = "bsb_profiling"
        self._current_f = None
        self._flushcounter = 0

    def set_name(self, name):
        self.name = name

    def start(self):
        if not self._started:
            self._started = True
            self.profile = cProfile.Profile()
            self.profile.enable()
            atexit.register(self.flush)

    def stop(self):
        if self._started:
            self._started = False
            self.profile.disable()
            atexit.unregister(self.flush)

    def flush(self, stats=True):
        profile = self.profile
        if self._current_f is None:
            uuid = uuid4()
            self._current_f = f"{self.name}_{MPI.get_rank()}_{uuid}"
        if stats:
            self.profile.dump_stats(f"{self._current_f}_{self._flushcounter}.prf")
            self._flushcounter += 1
        try:
            del self.profile
            with open(f"{self._current_f}.pkl", "wb") as f:
                pickle.dump(self, f)
        except Exception as e:
            warnings.warn(f"Could not store profile: {e}", stacklevel=2)
        finally:
            self.profile = profile

    def view(self):
        try:
            from snakeviz.cli import main as snakeviz
        except ImportError:
            raise ImportError("Please `pip install snakeviz` to view profiles.") from None

        args = sys.argv
        if self._current_f is None:
            self.flush()
        sys.argv = ["snakeviz", f"{self._current_f}.prf"]
        try:
            snakeviz()
        finally:
            sys.argv = args

    @staticmethod
    def load(fstem):
        with open(f"{fstem}.pkl", "rb") as f:
            return pickle.load(f)


@cache
def get_active_session():
    return ProfilingSession()


def activate_session(name=None):
    session = get_active_session()
    if name is not None:
        session.set_name(name)
    session.start()
    return session


def view_profile(fstem):
    ProfilingSession.load(fstem).view()


__all__ = [
    "ProfilingSession",
    "activate_session",
    "get_active_session",
    "view_profile",
]
_otel_tracer = trace.get_tracer("bsb", str(importlib.metadata.version("bsb-core")))


def _instrument_command(cls):
    _orig_handler = cls.handler

    @functools.wraps(cls.handler)
    def handler(self, context):
        attributes = {
            "bsb.type": "command_handler",
            "bsb.command_class": cls.__name__,
            "bsb.command_name": cls.name,
        }

        if hasattr(cls, "get_options"):
            attributes["bsb.command_options"] = [
                f"{k}={getattr(context, k)}" for k, v in self.get_options().items()
            ]

        with _otel_tracer.start_as_current_span(
            cls.name,
            attributes=attributes,
        ):
            return _orig_handler(self, context)

    cls.handler = handler
    return cls


def _get_implemented_abstracts(cls):
    """Return dict mapping base class → set of abstract methods implemented in cls."""
    result = {}
    subclass_abstracts = getattr(cls, "__abstractmethods__", frozenset())
    for base in cls.__mro__:
        if not hasattr(base, "__abstractmethods__"):
            continue
        base_abstracts = base.__abstractmethods__
        # Abstract methods from this base that are now implemented in cls
        implemented = base_abstracts - subclass_abstracts
        if implemented:
            result[base] = implemented
    return result


def _instrument_node(cls):
    for base, implemented in _get_implemented_abstracts(cls).items():
        for attr in implemented:
            orig_method = getattr(cls, attr)
            if inspect.isfunction(orig_method):
                wrapped = _make_otel_handler(cls, base, attr, orig_method)
                setattr(cls, attr, wrapped)


def _make_otel_handler(cls, base, attr, orig_method):
    """Return a wrapper function for a single method."""

    @functools.wraps(orig_method)
    def handler(self, *args, **kwargs):
        with _otel_tracer.start_as_current_span(
            f"{cls.__name__}.{attr}",
            attributes={
                "bsb.type": "component_method",
                "bsb.component_type": base.__name__,
                "bsb.component_class": cls.__name__,
                "bsb.component_method": attr,
                "bsb.component_attributes": json.dumps(self.__tree__()),
            },
        ):
            return orig_method(self, *args, **kwargs)

    return handler
