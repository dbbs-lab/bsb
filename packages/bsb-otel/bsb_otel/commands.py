"""
``bsb`` CLI commands contributed by ``bsb-otel``.

Registered under the ``bsb.commands`` plugin group. This module is imported by
the BSB CLI's command discovery, not by ``opentelemetry-instrument``, so it may
import ``bsb`` freely. It does not import the OpenTelemetry SDK at module level:
the SDK-only ``replay`` logic is imported inside the handler so that ``bsb``
keeps working for users who installed ``bsb-otel`` without the ``[sdk]`` extra.
"""

from bsb.cli.commands import BaseCommand


class BsbReplayOtel(BaseCommand, name="replay-otel"):
    """
    Replay one or more JSON Lines trace files into the active OpenTelemetry
    pipeline. Run under ``opentelemetry-instrument`` so the configured exporter
    forwards the replayed spans, e.g. to a Jaeger collector::

        opentelemetry-instrument \\
            --traces_exporter otlp \\
            --exporter_otlp_endpoint http://localhost:4317 \\
            --service_name "BSB Replay" \\
            bsb replay-otel traces_*.jsonlines
    """

    def get_options(self):
        return {}

    def add_parser_arguments(self, parser):
        parser.add_argument(
            "files",
            nargs="+",
            help="JSON Lines trace file(s) or glob pattern(s) to replay.",
        )
        parser.add_argument(
            "--keep-timestamps",
            action="store_true",
            help="Keep the original timestamps instead of shifting the trace to "
            "end now (you may then need to widen the collector's search window).",
        )

    def handler(self, context):
        from bsb_otel.replay import replay_files

        replay_files(
            context.arguments.files,
            shift_to_now=not context.arguments.keep_timestamps,
        )
