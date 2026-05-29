"""
OpenTelemetry distro/configurator that wires a BSB-compatible ldjson exporter.

The jsonlines pipeline is gated, not default-on. It engages only when it is
explicitly asked for, either by selecting this distro
(``OTEL_PYTHON_DISTRO=bsb_jsonlines``) or by selecting the jsonlines exporter
(``--traces_exporter jsonlines`` / ``OTEL_TRACES_EXPORTER=jsonlines``).
Otherwise both classes defer to the stock OpenTelemetry distro and configurator,
so an ``opentelemetry-instrument`` run that wants a different exporter (e.g. OTLP
for ``bsb replay-otel``) is never hijacked, even though this distro is a
registered entry point and may be auto-selected ahead of the default one.

When engaged, the configurator builds a ``TracerProvider`` backed by a
``SimpleSpanProcessor`` (no daemon export thread), sidestepping the
``BatchSpanProcessor`` / mpi4py atexit deadlock on Python 3.12.

This module touches only OpenTelemetry, never ``bsb``, so it stays within the
entry-point DMZ (see :mod:`bsb_otel`).
"""

import os

from opentelemetry import trace
from opentelemetry.distro import OpenTelemetryConfigurator, OpenTelemetryDistro
from opentelemetry.environment_variables import OTEL_TRACES_EXPORTER
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from bsb_otel.exporters import JSONLinesSpanExporter

# opentelemetry-api does not re-export these as constants (checked up to main);
# use the literal env var names.
_OTEL_PYTHON_DISTRO = "OTEL_PYTHON_DISTRO"
_OTEL_PYTHON_CONFIGURATOR = "OTEL_PYTHON_CONFIGURATOR"
_NAME = "bsb_jsonlines"


def _jsonlines_selected():
    exporters = os.environ.get(OTEL_TRACES_EXPORTER, "")
    return "jsonlines" in (e.strip() for e in exporters.split(","))


class BsbJsonlinesDistro(OpenTelemetryDistro):
    def _configure(self, **kwargs):
        if os.environ.get(_OTEL_PYTHON_DISTRO) != _NAME:
            # Auto-selected rather than explicitly requested: behave like the
            # stock distro and leave exporter selection untouched.
            return super()._configure(**kwargs)
        os.environ.setdefault(OTEL_TRACES_EXPORTER, "jsonlines")
        os.environ.setdefault(_OTEL_PYTHON_CONFIGURATOR, _NAME)


class BsbJsonlinesConfigurator(OpenTelemetryConfigurator):
    def _configure(self, **kwargs):
        requested = (
            os.environ.get(_OTEL_PYTHON_CONFIGURATOR) == _NAME or _jsonlines_selected()
        )
        if not requested:
            # Auto-selected without the jsonlines pipeline being asked for:
            # defer to the stock SDK configurator (OTLP, console, ...).
            return super()._configure(**kwargs)
        if trace._TRACER_PROVIDER is not None:
            return
        provider = TracerProvider()
        provider.add_span_processor(SimpleSpanProcessor(JSONLinesSpanExporter()))
        trace.set_tracer_provider(provider)
