"""
Out-of-process NEST kernel proxy.

Runs NEST in a child process behind a
:class:`multiprocessing.managers.BaseManager` so the main process can query
``GetDefaults`` / ``Install`` / ``Models`` during configuration building
without mutating an in-process NEST kernel.

The proxy is created lazily on first call to :func:`get_nest_kernel_proxy`,
stored on the active :class:`~bsb.config.BuildContext` at
``ctx.bsb_nest.kernel``, and shut down by a cleanup callback when the build
context exits.
"""

from multiprocessing.managers import BaseManager

from bsb import ConfigurationError
from bsb.config import get_config_build_context


class _NestKernel:
    """In-subprocess wrapper around ``nest`` so its global state stays there.

    Methods return only basic Python types so multiprocessing can pickle them
    back to the parent. NEST's SLI objects (``SLIDict``, ``SLIDatum``) are not
    picklable.
    """

    def __init__(self):
        import nest  # imported in the child process only

        self._nest = nest
        self._loaded = set()

    def install(self, module):
        try:
            self._nest.Install(module)
        except Exception as e:
            # Re-installing a module is benign; surface any other failure.
            if getattr(e, "errorname", "") == "DynamicModuleManagementError" and (
                "loaded already" in getattr(e, "message", "")
            ):
                return
            raise

    def load_modules(self, modules):
        """Install NEST *modules*, skipping any already loaded for this build.

        Returns the names of any *modules* that could not be found, so the
        caller can turn them into a configuration error. One proxy is reused for
        the whole build, so several validators may ask for the same simulation's
        modules; tracking what is loaded keeps each module's ``Install`` to a
        single call.
        """
        missing = []
        for module in modules:
            if module in self._loaded:
                continue
            try:
                self.install(module)
            except Exception as e:
                if getattr(e, "errorname", "") == "DynamicModuleManagementError" and (
                    "file not found" in getattr(e, "message", "")
                ):
                    missing.append(module)
                    continue
                raise
            self._loaded.add(module)
        return missing

    def has_delay(self, model):
        return bool(self._nest.GetDefaults(model)["has_delay"])

    def models(self, mtype=None):
        return [
            str(m)
            for m in (self._nest.Models(mtype=mtype) if mtype else self._nest.Models())
        ]


class NestKernelManager(BaseManager):
    """:class:`BaseManager` that exposes :class:`_NestKernel` to the parent."""


NestKernelManager.register(
    "kernel",
    _NestKernel,
    exposed=("install", "load_modules", "has_delay", "models"),
)


def _start_kernel_manager():
    manager = NestKernelManager()
    manager.start()
    return manager


def get_nest_kernel_proxy():
    """
    Return a proxy to the out-of-process NEST kernel for this build.

    Returns ``None`` when called outside an active configuration build; callers
    should treat that as "can't reach the kernel" and fall back gracefully.
    """
    ctx = get_config_build_context()
    if ctx is None:
        return None
    # `ctx.bsb_nest` auto-vivifies the namespace; the leaf read goes via
    # __dict__ so a missing kernel stays missing (auto-vivify would otherwise
    # return an empty namespace and mask the "not yet started" state).
    ns = ctx.bsb_nest
    existing = ns.__dict__.get("kernel")
    if existing is not None:
        return existing
    manager = _start_kernel_manager()
    proxy = manager.kernel()
    ns.kernel = proxy
    ns.kernel_manager = manager
    ctx.add_cleanup(manager.shutdown)
    return proxy


def load_simulation_modules(node, proxy):
    """Install a config *node*'s enclosing simulation modules into the *proxy*.

    Walks up from *node* to the owning ``NestSimulation`` and hands its
    ``modules`` to :meth:`_NestKernel.load_modules`, which installs each module
    only once per build. Raises :class:`~bsb.exceptions.ConfigurationError` if a
    module can't be found. No-op when *node* has no enclosing simulation, e.g. a
    model built in isolation.
    """
    parent = getattr(node, "_config_parent", None)
    while parent is not None:
        modules = getattr(parent, "modules", None)
        if isinstance(modules, (list, tuple)):
            missing = proxy.load_modules(list(modules))
            if missing:
                raise ConfigurationError(
                    f"NEST module(s) not found: {', '.join(missing)}."
                )
            return
        parent = getattr(parent, "_config_parent", None)
