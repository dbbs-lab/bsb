from bsb_otel.testing import wrap_tests_with_traces


def load_tests(loader, tests, pattern):
    """
    Loads all the tests in the test suite and wraps the cases in otel traces.

    This method is called by the unittest module during test discovery.
    """

    # Re-run discovery without the top_level_dir argument, to load all tests
    # without triggering exactly this loader (which would loop infinitely)
    suite = loader.discover("tests")

    # Then visit the tree to wrap each test case in OTel logic
    wrap_tests_with_traces(suite)

    # Return the modified test suite
    return suite
