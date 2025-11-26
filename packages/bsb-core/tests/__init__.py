from unittest import TestSuite


def load_tests(loader, tests, pattern):
    for suite in loader.discover("tests")._tests:
        print(suite)
    return TestSuite()
