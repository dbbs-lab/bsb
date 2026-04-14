import importlib.metadata

from opentelemetry import trace

_hdf5_tracer = trace.get_tracer("bsb-hdf5", importlib.metadata.version("bsb-hdf5"))
