"""
BSB services: thin shims over swappable backends.

Each service submodule (``bsb.services.mpi``, ``bsb.services.mpilock``,
``bsb.services.pool``) is a *reference stub* documenting the contract a
provider must satisfy. At import time this package resolves a provider for
each service according to user preference (env var or project option) and
installs the resolved provider module into ``sys.modules[bsb.services.<name>]``
before any consumer can import it. The stub ``.py`` file on disk is therefore
never executed at runtime; it exists only as a contract for IDEs and static
checkers.

Entry-point convention
----------------------

Provider packages register modules in the ``bsb.providers.<service>`` group::

    [project.entry-points."bsb.providers.mpi"]
    mpi4py = "bsb._providers.mpi.mpi4py_loader:load"
    serial = "bsb._providers.mpi.serial"

The entry-point value is either:

* a **callable** returning a module — used when probing requires
  side-effectful imports. The callable must raise
  :class:`bsb.exceptions.ProviderUnavailableError` if the backend is missing.
* a **module** — installed directly, used when import is cheap and pure.

User preference
---------------

Users select providers with the env vars ``BSB_PROVIDE_MPI``,
``BSB_PROVIDE_MPILOCK``, ``BSB_PROVIDE_POOL`` (or the matching project options).
The value is an ordered, comma-separated list of provider names. The resolver
tries them in order; the first that loads wins. If the list exhausts with no
success, the framework refuses to start.
"""

import importlib
import importlib.metadata
import pkgutil
import sys

from .. import options as _options
from ..exceptions import DependencyError, ProviderUnavailableError

_ENTRY_POINT_GROUP = "bsb.providers"
_RESOLVED: dict[str, str] = {}


def _discover_stubs() -> list[str]:
    return [
        name
        for _finder, name, _ispkg in pkgutil.iter_modules(__path__)
        if not name.startswith("_")
    ]


def _read_preference(service: str) -> list[str]:
    raw = _options.get_module_option(f"provide_{service}")
    if isinstance(raw, str):
        return [name.strip() for name in raw.split(",") if name.strip()]
    if raw is None:
        return []
    return list(raw)


def _entry_points(service: str) -> dict[str, importlib.metadata.EntryPoint]:
    eps = importlib.metadata.entry_points(group=f"{_ENTRY_POINT_GROUP}.{service}")
    return {ep.name: ep for ep in eps}


def _load_provider(ep: importlib.metadata.EntryPoint):
    target = ep.load()
    if callable(target) and not _looks_like_module(target):
        return target()
    return target


def _looks_like_module(obj) -> bool:
    return hasattr(obj, "__name__") and hasattr(obj, "__loader__")


_SERVICE_SYMBOLS = {
    "mpi": "MPI",
    "mpilock": "MPILock",
    "pool": "Pool",
}


def _install(service: str, module) -> None:
    full = f"{__name__}.{service}"
    sys.modules[full] = module
    pkg = sys.modules[__name__]
    setattr(pkg, service, module)
    # Re-export the provider's primary symbol on bsb.services for convenience,
    # so `from bsb.services import MPI/MPILock/Pool` keeps working.
    symbol = _SERVICE_SYMBOLS.get(service)
    if symbol and hasattr(module, symbol):
        setattr(pkg, symbol, getattr(module, symbol))


def _resolve(service: str) -> None:
    preference = _read_preference(service)
    if not preference:
        raise DependencyError(
            f"No providers configured for bsb service '{service}'. Set "
            f"BSB_PROVIDE_{service.upper()} to a comma-separated list of "
            f"provider names."
        )
    eps = _entry_points(service)
    tried: list[str] = []
    for name in preference:
        if name not in eps:
            tried.append(f"{name} (no entry point registered)")
            continue
        try:
            module = _load_provider(eps[name])
        except ProviderUnavailableError as exc:
            tried.append(f"{name} ({exc})")
            continue
        _install(service, module)
        _RESOLVED[service] = name
        return
    raise DependencyError(
        f"No usable provider for bsb service '{service}'. Tried: "
        + "; ".join(tried)
    )


def get_resolved(service: str) -> str:
    """Return the provider name that resolved for ``service``."""
    return _RESOLVED[service]


for _service in _discover_stubs():
    _resolve(_service)

del _service
