import functools
import json
import os
import tempfile
import typing
import unittest
from collections import deque

from opentelemetry import trace


def _pop(queue):
    try:
        return queue.pop()
    except IndexError:
        return None


def _visit_test_cases(root, visitor):
    queue = deque([root])
    while node := _pop(queue):
        if isinstance(node, unittest.TestCase):
            visitor(node)
        else:
            queue.extend(reversed(list(node)))


def _wrap_case(case: unittest.TestCase):
    original_run = case.run
    cls = type(case)
    cls_name = cls.__name__

    def wrapped_run(*args, **kwargs):
        from bsb_otel import get_bsb_tracer

        with get_bsb_tracer("bsb-otel").trace(
            case.id(),
            attributes={
                "python.test_package": case.id().split(".")[0],
                "python.test_module": case.id().split(".")[1],
                "python.test_class": case.id().split(".")[2],
                "python.test_case": case.id().split(".")[3],
            },
        ):
            return original_run(*args, **kwargs)

    case.run = wrapped_run

    # Wrap setUp/tearDown — walk the MRO so mixin-defined hooks are found.
    # Skip only if the hook resolves to unittest.TestCase's own no-op.
    for hook_name in ("setUp", "tearDown"):
        defining_base = next((b for b in cls.__mro__ if hook_name in b.__dict__), None)
        if defining_base is None or defining_base is unittest.TestCase:
            continue
        orig = getattr(case, hook_name)

        def make_wrapper(original, name):
            def wrapped_hook(*args, **kwargs):
                from bsb_otel import get_bsb_tracer

                with get_bsb_tracer("bsb-otel").trace(f"{cls_name}.{name}"):
                    return original(*args, **kwargs)

            return wrapped_hook

        setattr(case, hook_name, make_wrapper(orig, hook_name))


def _wrap_class_hooks(cls):
    # Wrap setUpClass/tearDownClass — walk the MRO so mixin-defined hooks are found.
    # Skip only if the hook resolves to unittest.TestCase's own no-op.
    for hook_name in ("setUpClass", "tearDownClass"):
        defining_base = next((b for b in cls.__mro__ if hook_name in b.__dict__), None)
        if defining_base is None or defining_base is unittest.TestCase:
            continue
        descriptor = defining_base.__dict__[hook_name]
        # Unwrap the classmethod descriptor to get the raw function.
        inner = descriptor.__func__ if isinstance(descriptor, classmethod) else descriptor

        def make_wrapper(func, name, cls_name=cls.__name__):
            @classmethod
            @functools.wraps(func)
            def wrapped(klass, *args, **kwargs):
                from bsb_otel import get_bsb_tracer

                with get_bsb_tracer("bsb-otel").trace(f"{cls_name}.{name}"):
                    return func(klass, *args, **kwargs)

            return wrapped

        setattr(cls, hook_name, make_wrapper(inner, hook_name))


def wrap_tests_with_traces(suite):
    """
    Wrap every :class:`unittest.TestCase` in *suite* so that each test run is
    recorded as an OpenTelemetry trace span.

    Also wraps ``setUpClass``/``tearDownClass`` (as standalone broadcast spans)
    and ``setUp``/``tearDown`` (as sub-spans within the test run span) when the
    class defines them.

    Intended to be called from a ``load_tests`` hook::

        from bsb_otel.testing import wrap_tests_with_traces


        def load_tests(loader, tests, pattern):
            suite = loader.discover("tests")
            wrap_tests_with_traces(suite)
            return suite
    """
    seen_classes = set()

    def wrap_case_and_class(case):
        _wrap_case(case)
        cls = type(case)
        if cls not in seen_classes:
            seen_classes.add(cls)
            _wrap_class_hooks(cls)

    _visit_test_cases(suite, wrap_case_and_class)


def _get_file_tracer_provider(file: typing.IO, buffered=True):
    """
    Create a provider that exports traces to a file as JSON lines.
    """
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )

    exporter = ConsoleSpanExporter(
        out=file, formatter=lambda span: span.to_json(indent=None) + os.linesep
    )
    processor = (BatchSpanProcessor if buffered else SimpleSpanProcessor)(exporter)
    provider = TracerProvider()
    provider.add_span_processor(processor)

    return provider


class OTelFixture:
    """
    Context manager that overrides the global tracer provider with a custom one
    that exports to a temporary file, allowing tests to assert on recorded spans.

    The global tracer provider is restored on exit.

    Usage::

        with OTelFixture() as results:
            handle_command(["--version"])

        spans = results()
        assert spans[0]["name"] == "cli"
    """

    def __enter__(self):
        try:
            import opentelemetry.sdk  # noqa: F401
        except ImportError:
            raise ImportError(
                "OTelFixture requires the OpenTelemetry SDK. "
                "Install it with: pip install 'bsb-otel[sdk]'"
            ) from None
        import bsb_otel as _bsb_otel

        self._old_provider = trace.get_tracer_provider()
        self.temp_file = tempfile.NamedTemporaryFile("w+")
        provider = _get_file_tracer_provider(file=self.temp_file)
        # Note: overriding _TRACER_PROVIDER is not officially supported by OTel.
        trace._TRACER_PROVIDER = provider
        # OTel's ProxyTracer locks its delegate to the first real provider it sees
        # and never re-delegates, so simply swapping _TRACER_PROVIDER is not enough
        # for re-entrant use.  Replace each registered BsbTracer's internal tracer
        # with a fresh one from the fixture's provider.
        self._old_tracers = {
            name: bt._otel_tracer for name, bt in _bsb_otel._tracer_registry.items()
        }
        for name, bt in _bsb_otel._tracer_registry.items():
            bt._otel_tracer = provider.get_tracer(name, bt._version)

        def reader():
            if not hasattr(self, "results"):
                raise RuntimeError("Reader called before end of context")
            return self.results

        return reader

    def __exit__(self, exc_type, exc_val, exc_tb):
        import bsb_otel as _bsb_otel

        provider = trace.get_tracer_provider()
        provider.shutdown()
        trace._TRACER_PROVIDER = self._old_provider
        # Restore each pre-existing BsbTracer's internal tracer.
        for name, old_tracer in self._old_tracers.items():
            if name in _bsb_otel._tracer_registry:
                _bsb_otel._tracer_registry[name]._otel_tracer = old_tracer
        # Drop any BsbTracers created during the fixture — they hold a stale
        # fixture tracer and will be re-created correctly on next use.
        for name in list(_bsb_otel._tracer_registry):
            if name not in self._old_tracers:
                del _bsb_otel._tracer_registry[name]
        self.temp_file.seek(0)
        self.results = [json.loads(line) for line in self.temp_file.readlines()]
        self.temp_file.close()


__all__ = ["OTelFixture", "wrap_tests_with_traces"]
