from bsb_otel.testing import wrap_tests_with_traces


def load_tests(loader, tests, pattern):
    """
    Loads all the tests in the test suite and wraps the cases in otel traces.

    This method is called by the unittest module during test discovery.
    """

    # Use the pattern passed by the caller (e.g. via -p "test_connectivity2.py")
    # Fall back to the loader's default if none was given
    effective_pattern = pattern or loader.testNamePatterns or "test*.py"

    # Discover respecting the pattern, without top_level_dir to avoid
    # re-triggering this load_tests and looping infinitely
    suite = loader.discover("tests", pattern=effective_pattern)

    # Then visit the tree to wrap each test case in OTel logic
    wrap_tests_with_traces(suite)

    # Return the modified test suite
    return suite
