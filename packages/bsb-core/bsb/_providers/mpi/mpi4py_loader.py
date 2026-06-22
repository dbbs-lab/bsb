"""Loader for the mpi4py MPI provider."""

from ...exceptions import ProviderUnavailableError


def load():
    try:
        import mpi4py  # noqa: F401  # cheap top-level import
    except ImportError as exc:  # pragma: nocover
        raise ProviderUnavailableError("mpi4py is not installed") from exc
    from . import mpi4py as provider

    return provider
