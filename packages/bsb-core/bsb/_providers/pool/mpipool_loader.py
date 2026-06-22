"""Loader for the mpipool Pool provider."""

from ...exceptions import ProviderUnavailableError


def load():
    try:
        import mpipool  # noqa: F401
    except ImportError as exc:  # pragma: nocover
        raise ProviderUnavailableError("mpipool is not installed") from exc
    from . import mpipool as provider

    return provider
