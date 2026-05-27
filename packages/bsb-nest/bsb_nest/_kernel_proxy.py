"""
Out-of-process NEST kernel proxy.

NEST mutates global state on import; doing it in the user's main process at
configuration-build time is the surprise documented in dbbs-lab/bsb#227. This
module runs NEST in a child process behind a
:class:`multiprocessing.managers.BaseManager` so the main process can query
``GetDefaults`` / ``Install`` / ``Models`` without ever importing ``nest``.

The proxy is created lazily on first call to :func:`get_nest_kernel_proxy`,
stored on the active :class:`~bsb.config.BuildContext` at
``ctx.bsb_nest.kernel``, and shut down by a cleanup callback when the build
context exits.
"""

from multiprocessing.managers import BaseManager

from bsb.config import get_config_build_context


class _NestKernel:
    """In-subprocess wrapper around ``nest`` so its global state stays there.

    Methods return only basic Python types so multiprocessing can pickle them
    back to the parent — NEST's SLI objects (``SLIDict``, ``SLIDatum``) are
    not picklable.
    """

    def __init__(self):
        import nest  # imported in the child process only

        self._nest = nest

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
    exposed=("install", "has_delay", "models"),
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
