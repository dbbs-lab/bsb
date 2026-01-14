import unittest
from collections import deque

from bsb.profiling import _telemetry_trace


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

    def wrapped_run(*args, **kwargs):
        with _telemetry_trace(
            case.id(),
            attributes={
                "python.test_package": case.id().split(".")[0],
                "python.test_module": case.id().split(".")[1],
                "python.test_class": case.id().split(".")[2],
                "python.test_case": case.id().split(".")[3],
            },
            broadcast=True,
        ):
            return original_run(*args, **kwargs)

    case.run = wrapped_run


def load_tests(loader, tests, pattern):
    """
    Loads all the tests in the test suite and wraps the cases in otel traces.

    This method is called by the unittest module during test discovery.
    """

    # Re-run discovery without the top_level_dir argument, to load all tests
    # without triggering exactly this loader (which would loop infinitely)
    suite = loader.discover("tests")

    # Then visit the tree to wrap each test case in OTel logic
    _visit_test_cases(suite, _wrap_case)

    # Return the modified test suite
    return suite
