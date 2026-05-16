"""
OpenTelemetry distro that wires a BSB-compatible ldjson exporter.

Activated by ``OTEL_PYTHON_DISTRO=bsb_jsonlines`` when running under
``opentelemetry-instrument``. The distro pins our ``jsonlines`` exporter
and selects our companion configurator, which builds a TracerProvider
backed by a ``SimpleSpanProcessor`` (no daemon export thread — sidesteps
the BatchSpanProcessor / mpi4py atexit deadlock on Python 3.12).
"""

import os

from opentelemetry import trace
from opentelemetry.environment_variables import OTEL_TRACES_EXPORTER
from opentelemetry.instrumentation.distro import BaseDistro
from opentelemetry.sdk._configuration import _BaseConfigurator
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from bsb_otel.exporters import JSONLinesSpanExporter


class BsbJsonlinesDistro(BaseDistro):
    def _configure(self, **kwargs):
        os.environ.setdefault(OTEL_TRACES_EXPORTER, "jsonlines")
        # opentelemetry-api does not re-export OTEL_PYTHON_CONFIGURATOR as a
        # constant (checked up to main); use the literal env var name.
        os.environ.setdefault("OTEL_PYTHON_CONFIGURATOR", "bsb_jsonlines")


class BsbJsonlinesConfigurator(_BaseConfigurator):
    def _configure(self, **kwargs):
        if trace._TRACER_PROVIDER is not None:
            return
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(JSONLinesSpanExporter()))
        trace.set_tracer_provider(provider)
