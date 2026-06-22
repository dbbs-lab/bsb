"""Loader for the mpilock MPILock provider."""

from ...exceptions import ProviderUnavailableError


def load():
    try:
        import mpilock  # noqa: F401
    except ImportError as exc:  # pragma: nocover
        raise ProviderUnavailableError("mpilock is not installed") from exc
    from . import mpilock as provider

    return provider
