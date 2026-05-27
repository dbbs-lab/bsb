import functools
import sys

import numpy as np
import psutil
from bsb import ConfigurationError, ConnectionModel, compose_nodes, config, options, types, warn
from tqdm import tqdm

from ._kernel_proxy import get_nest_kernel_proxy
from .distributions import nest_parameter
from .exceptions import KernelWarning


def _is_delay_required(kwargs):
    """
    ``required=`` checker for :attr:`NestSynapseSettings.delay`.

    Asks the out-of-process NEST kernel whether the configured synapse model
    needs a delay. When the proxy is reachable, an unknown model name is a
    hard :class:`ConfigurationError` (matches the pre-#228 boot-time check).
    When the proxy can't be reached at all (no active build context, kernel
    spawn failed, IPC error), the checker downgrades to a warning + returns
    ``False`` so config loading stays robust; the real error surfaces later
    at adapter prepare/connect time.
    """
    model_name = kwargs.get("model", NestSynapseSettings.model.default)
    try:
        proxy = get_nest_kernel_proxy()
        if proxy is None:
            warn(
                "No active build context; cannot check whether synapse"
                f" '{model_name}' requires a delay.",
                KernelWarning,
            )
            return False
        _install_simulation_modules(kwargs, proxy)
        synapse_models = proxy.models(mtype="synapses")
    except ConfigurationError:
        raise
    except Exception as e:
        warn(
            f"Could not determine if delay is required for synapse"
            f" '{model_name}': {e}",
            KernelWarning,
        )
        return False
    # Model-name validation is independent of the soft delay-required check:
    # if we *can* reach the kernel, an unknown model is a real config error.
    if model_name not in synapse_models:
        raise ConfigurationError(f"Unknown synapse model '{model_name}'.")
    try:
        return proxy.has_delay(model_name)
    except Exception as e:
        warn(
            f"Could not determine if delay is required for synapse"
            f" '{model_name}': {e}",
            KernelWarning,
        )
        return False


def _install_simulation_modules(kwargs, proxy):
    """Walk up to the enclosing :class:`NestSimulation` and install its modules."""
    instance = getattr(kwargs, "instance", None)
    parent = getattr(instance, "_config_parent", None)
    while parent is not None:
        modules = getattr(parent, "modules", None)
        if isinstance(modules, (list, tuple)):
            for module in modules:
                proxy.install(module)
            return
        parent = getattr(parent, "_config_parent", None)


@config.node
class NestSynapseSettings:
    """
    Class interfacing a NEST synapse model.
    """

    model = config.attr(type=str, default="static_synapse")
    """Importable reference to the NEST model describing the synapse type."""
    weight = config.attr(type=float, required=True)
    """Weight of the connection between the presynaptic and the postsynaptic cells."""
    delay = config.attr(type=float, required=_is_delay_required, default=None)
    """Delay of the transmission between the presynaptic and the postsynaptic cells."""
    receptor_type = config.attr(type=int)
    """Index of the postsynaptic receptor to target."""
    constants = config.catch_all(type=nest_parameter())
    """Dictionary of the constants values to assign to the synapse model."""


@config.node
class NestConnectionSettings:
    """
    Class interfacing a NEST connection rule.
    """

    rule = config.attr(type=str)
    """Importable reference to the NEST connection rule used to connect the cells."""
    constants = config.catch_all(type=types.any_())
    """Dictionary of parameters to assign to the connection rule."""


class LazySynapseCollection:
    def __init__(self, pre, post):
        self._pre = pre
        self._post = post

    def __len__(self):
        return self.collection.__len__()

    def __str__(self):
        return self.collection.__str__()

    def __iter__(self):
        return iter(self.collection)

    def __getattr__(self, attr):
        return getattr(self.collection, attr)

    @functools.cached_property
    def collection(self):
        import nest

        return nest.GetConnections(self._pre, self._post)


@config.dynamic(attr_name="model_strategy", required=False)
class NestConnection(compose_nodes(NestConnectionSettings, ConnectionModel)):
    """
    Class interfacing a NEST connection, including its connection rule and synaptic
    parameters.
    """

    model_strategy: str
    """
    Specifies the strategy used by the connection model for synapse creation and
    management.
    """

    synapses = config.list(type=NestSynapseSettings, required=True)
    """List of synapse models to use for a connection."""

    def create_connections(self, simdata, pre_nodes, post_nodes, cs, comm):
        import nest

        syn_specs = self.get_syn_specs()
        if self.rule is not None:
            nest.Connect(
                pre_nodes,
                post_nodes,
                self.get_conn_spec(),
                nest.CollocatedSynapses(*syn_specs),
            )
        else:
            comm.barrier()
            for pre_locs, post_locs in self.predict_mem_iterator(
                pre_nodes, post_nodes, cs, comm
            ):
                comm.barrier()
                if len(pre_locs) == 0 or len(post_locs) == 0:
                    continue
                cell_pairs, multiplicity = np.unique(
                    np.column_stack((pre_locs[:, 0], post_locs[:, 0])),
                    return_counts=True,
                    axis=0,
                )
                prel = pre_nodes.tolist()
                postl = post_nodes.tolist()
                # cannot use CollocatedSynapses with a list of weight and delay
                # so loop over the syn_specs
                for syn_spec in syn_specs:
                    ssw = {**syn_spec}
                    bw = syn_spec["weight"]
                    ssw["weight"] = [bw * m for m in multiplicity]
                    if "delay" in syn_spec:
                        ssw["delay"] = [syn_spec["delay"]] * len(ssw["weight"])
                    nest.Connect(
                        [prel[x] for x in cell_pairs[:, 0]],
                        [postl[x] for x in cell_pairs[:, 1]],
                        "one_to_one",
                        ssw,
                        return_synapsecollection=False,
                    )
            comm.barrier()
        return LazySynapseCollection(pre_nodes, post_nodes)

    def predict_mem_iterator(self, pre_nodes, post_nodes, cs, comm):
        avmem = psutil.virtual_memory().available
        predicted_all_mem = (
            len(pre_nodes) * 8 * 2 + len(post_nodes) * 8 * 2 + len(cs) * 6 * 8 * (16 + 2)
        ) * comm.get_size()
        n_chunks = len(cs.get_local_chunks("out"))
        predicted_local_mem = (predicted_all_mem / n_chunks) if n_chunks > 0 else 0.0
        if predicted_local_mem > avmem / 2:
            # Iterate block-by-block
            return self.block_iterator(cs, comm)
        elif predicted_all_mem > avmem / 2:
            # Iterate local hyperblocks
            return self.local_iterator(cs, comm)
        else:
            # Iterate all
            return (cs.load_connections().as_globals().all(),)

    def block_iterator(self, cs, comm):
        locals = cs.get_local_chunks("out")

        def block_iter():
            iter = locals
            if comm.get_rank() == 0:
                iter = tqdm(
                    iter,
                    desc="hyperblocks",
                    file=sys.stdout,
                    disable=options.verbosity < 2,
                )
            for local in iter:
                inner_iter = cs.load_connections().as_globals().from_(local)
                if comm.get_rank() == 0:
                    yield from tqdm(
                        inner_iter,
                        desc="blocks",
                        total=len(cs.get_global_chunks("out", local)),
                        file=sys.stdout,
                        leave=False,
                    )
                else:
                    yield from inner_iter

        return block_iter()

    def local_iterator(self, cs, comm):
        iter = cs.get_local_chunks("out")
        if comm.get_rank() == 0:
            iter = tqdm(
                iter, desc="hyperblocks", file=sys.stdout, disable=options.verbosity < 2
            )
        yield from (
            cs.load_connections().as_globals().from_(local).all() for local in iter
        )

    def get_connectivity_set(self):
        if self.tag is not None:
            return self.scaffold.get_connectivity_set(self.tag)
        else:
            return self.connection_model

    def get_conn_spec(self):
        return {
            "rule": self.rule,
            **self.constants,
        }

    def get_syn_specs(self):
        return [
            {
                **{
                    label: value
                    for attr, label in (
                        ("model", "synapse_model"),
                        ["weight"] * 2,
                        ["delay"] * 2,
                        ["receptor_type"] * 2,
                    )
                    if (value := getattr(synapse, attr)) is not None
                },
                **synapse.constants,
            }
            for synapse in self.synapses
        ]
