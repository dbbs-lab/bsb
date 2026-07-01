import functools
import sys

import numpy as np
import psutil
from bsb import (
    ConnectionModel,
    ConnectionParameter,
    compose_nodes,
    config,
    options,
    types,
    warn,
)
from bsb.config._attrs import cfgdict
from tqdm import tqdm

from ._kernel_proxy import NestModelTypeHandler, query_kernel
from .distributions import NestRandomDistribution, nest_constant


class nest_synapse_model(NestModelTypeHandler):
    """Validate a NEST synapse model name against the build's kernel."""

    mtype = "synapses"
    kind = "synapse"


def _is_delay_required(kwargs):
    """
    ``required=`` checker for :attr:`NestSynapseSettings.delay`.

    Asks the out-of-process NEST kernel whether the configured synapse model
    needs a delay. The model name itself is validated by
    :class:`~bsb_nest._kernel_proxy.NestModelTypeHandler` on the ``model``
    attribute. When the kernel can't be reached (no active build context,
    kernel spawn failed, IPC error), the checker downgrades to a warning and
    returns ``False`` so config loading stays robust; the real error surfaces
    later at adapter prepare/connect time.
    """
    model_name = kwargs.get("model", NestSynapseSettings.model.default)
    return query_kernel(
        getattr(kwargs, "partial_node", None),
        lambda proxy: proxy.has_delay(model_name),
        fallback=False,
        error_context=(
            f"Could not determine if delay is required for synapse '{model_name}'"
        ),
        unreachable_warning=(
            "No active build context; cannot check whether synapse"
            f" '{model_name}' requires a delay."
        ),
    ) and "delay" not in kwargs.get("parameters", NestSynapseSettings.parameters.default)


def _is_weight_required(kwargs):
    return "weight" not in kwargs.get(
        "parameters", NestSynapseSettings.parameters.default
    )


@config.node
class NestSynapseSettings:
    """
    Class interfacing a NEST synapse model.
    """

    model = config.attr(type=nest_synapse_model(), default="static_synapse")
    """Importable reference to the NEST model describing the synapse type."""
    parameters: cfgdict[ConnectionParameter] = config.dict(
        type=ConnectionParameter, default={}
    )
    """Dictionary of the parameters, computed during simulation loading, 
       to assign to the synapse model."""
    weight = config.attr(type=nest_constant(), required=_is_weight_required, default=None)
    """Weight of the connection between the presynaptic and the postsynaptic cells."""
    delay = config.attr(type=nest_constant(), required=_is_delay_required, default=None)
    """Delay of the transmission between the presynaptic and the postsynaptic cells."""
    receptor_type = config.attr(type=int)
    """Index of the postsynaptic receptor to target."""
    constants = config.catch_all(type=nest_constant())
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

        if self.rule is not None:
            nest.Connect(
                pre_nodes,
                post_nodes,
                self.get_conn_spec(),
                nest.CollocatedSynapses(*self.get_syn_specs()),
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
                for syn_spec in self.get_syn_specs(cs, pre_locs, post_locs):
                    ssw = {**syn_spec}
                    for k, v in ssw.items():
                        if isinstance(v, list | np.ndarray):
                            ssw[k] = np.repeat(v, multiplicity)
                        elif k == "weight":
                            ssw[k] = [v * m for m in multiplicity]
                        elif k == "delay":
                            ssw[k] = [v] * len(multiplicity)

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

    def get_syn_specs(self, cs=None, pre_locs=None, post_locs=None):
        syn_specs = []
        for synapse in self.synapses:
            # default values, can be overwritten by constants or parameters
            dict_syn = {
                "synapse_model": synapse.model,
                "weight": (
                    synapse.weight()
                    if isinstance(synapse.weight, NestRandomDistribution)
                    else synapse.weight
                ),
            }
            if synapse.delay is not None:
                dict_syn["delay"] = (
                    synapse.delay()
                    if isinstance(synapse.delay, NestRandomDistribution)
                    else synapse.delay
                )
            if synapse.receptor_type is not None:
                dict_syn["receptor_type"] = synapse.receptor_type
            for k, v in synapse.constants.items():
                dict_syn[k] = v() if isinstance(v, NestRandomDistribution) else v
            if cs is not None and pre_locs is not None and post_locs is not None:
                # can compute one sim param per connection pair
                dict_syn.update(
                    {
                        k: param.compute(self.simulation, cs, pre_locs, post_locs)
                        for k, param in synapse.parameters.items()
                    }
                )
            elif len(synapse.parameters) > 0:
                warn(
                    f"{self.model_strategy}: Parameters of synapse {synapse.model} will "
                    "be ignored as they rely on the reconstruction context. "
                    "Use `constants` instead."
                )
            syn_specs.append(dict_syn)

        return syn_specs
