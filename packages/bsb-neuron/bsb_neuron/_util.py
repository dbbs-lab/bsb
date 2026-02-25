import contextlib
import warnings

from arborize.exceptions import ProxyWarning


@contextlib.contextmanager
def ignore_arborize_proxy_warnings():
    try:
        catch = warnings.catch_warnings(category=ProxyWarning)
    except TypeError:
        # Python 3.10: This catches all warnings, sorry if this bites you.
        # todo: remove when dropping support for Python 3.10 (EOL Oct 2026)
        catch = warnings.catch_warnings()

    with catch:
        yield
