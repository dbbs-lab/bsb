import os
import random
import string
import typing

try:
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.sdk.trace.export import SpanExporter
except ImportError:
    raise ImportError(
        "bsb_otel.exporters requires the OpenTelemetry SDK. "
        "Install it with: pip install 'bsb-otel[sdk]'"
    ) from None

from bsb_otel._otel_env import OTEL_EXPORTER_JSONLINES_PATH


class JSONLinesSpanExporter(SpanExporter):
    """
    OpenTelemetry span exporter that writes spans as JSON lines to a file.

    The output path is read from the ``OTEL_EXPORTER_JSONLINES_PATH`` environment
    variable (default: ``traces_*.jsonlines``). A ``*`` in the path is replaced
    with a random 8-character alphanumeric string for unique filenames.

    Register as a traces exporter with opentelemetry-instrument::

        OTEL_EXPORTER_JSONLINES_PATH=./logs.jsonlines \\
            opentelemetry-instrument --traces_exporter jsonlines bsb compile
    """

    def __init__(self):
        from opentelemetry.sdk.trace.export import SpanExportResult

        self._result_ok = SpanExportResult.SUCCESS

        path = os.environ.get(OTEL_EXPORTER_JSONLINES_PATH, "traces_*.jsonlines")
        if "*" in path:
            path = path.replace(
                "*",
                "".join(random.choices(string.ascii_lowercase + string.digits, k=8)),
            )
        self._file = open(path, "a")  # noqa: SIM115

    def export(self, spans: typing.Sequence[ReadableSpan]):
        for span in spans:
            self._file.write(span.to_json(indent=None) + os.linesep)
        self._file.flush()
        return self._result_ok

    def shutdown(self):
        self._file.close()

    def force_flush(self, timeout_millis=30000):
        self._file.flush()
        return True


__all__ = ["JSONLinesSpanExporter"]
