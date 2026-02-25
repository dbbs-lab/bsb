"""
OpenTelemetry environment variable declarations for bsb exporters.

Registered under the ``opentelemetry_environment_variables`` entry point so
that ``opentelemetry-instrument`` automatically exposes these as CLI flags.
"""

OTEL_EXPORTER_JSONLINES_PATH = "OTEL_EXPORTER_JSONLINES_PATH"