import builtins
import functools
import sys

import numpy as np
import psutil
from bsb import (
    AdapterError,
    ConnectionModel,
    ConnectionParameter,
    ParameterizedModel,
    compose_nodes,
    config,
    options,
    types,
)
from tqdm import tqdm

from ._kernel_proxy import NestModelTypeHandler, query_kernel
from .distributions import nest_constant, nest_parameter


class nest_synapse_model(NestModelTypeHandler):
    """Validate a NEST synapse model name against the build's kernel."""

    mtype = "synapses"
    kind = "synapse"


def _is_weight_required(kwargs):
    """
    ``required=`` checker for :attr:`NestSynapseSettings.weight`.

    A weight is always needed, but it may be given as a computed parameter instead
    of as this attribute. ``constants`` is the node's catch-all, so a declared
    attribute never lands there; only ``parameters`` can stand in for it.
    """
    return "weight" not in kwargs.get("parameters", {})


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
    if "delay" in kwargs.get("parameters", {}):
        return False
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
    )


@config.node
class NestSynapseSettings(ParameterizedModel):
    """
    Class interfacing a NEST synapse model.
    """

    model = config.attr(type=nest_synapse_model(), default="static_synapse")
    """Importable reference to the NEST model describing the synapse type."""
    weight = config.attr(
        type=nest_parameter(ConnectionParameter), required=_is_weight_required
    )
    """Weight of the connection between the presynaptic and the postsynaptic cells."""
    delay = config.attr(
        type=nest_parameter(ConnectionParameter),
        required=_is_delay_required,
        default=None,
    )
    """Delay of the transmission between the presynaptic and the postsynaptic cells."""
    receptor_type = config.attr(type=nest_parameter(ConnectionParameter))
    """Index of the postsynaptic receptor to target."""
    constants = config.catch_all(type=nest_constant())
    """
    Constant values to assign to the synapse model, written directly on the node.

    A computed parameter belongs in :attr:`parameters`.
    """
    parameters = config.dict(type=nest_parameter(ConnectionParameter))
    """
    Parameters of the synapse model, resolved when the simulation loads.

    Accepts everything :attr:`constants` does, plus a ``strategy`` node selecting a
    :class:`~bsb.simulation.parameter.ConnectionParameter` computed per connection.
    """

    def get_parameter_groups(self):
        named = {
            name: value
            for name in ("weight", "delay", "receptor_type")
            if (value := getattr(self, name)) is not None
        }
        return (named, self.constants, self.parameters)


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
                # Several connections may join the same pair of cells; NEST is asked
                # for one connection per pair, carrying the summed weight. `take` is
                # the first row of each pair, which is where a per-connection
                # parameter's value for that pair is read from.
                cell_pairs, take, multiplicity = np.unique(
                    np.column_stack((pre_locs[:, 0], post_locs[:, 0])),
                    return_index=True,
                    return_counts=True,
                    axis=0,
                )
                prel = pre_nodes.tolist()
                postl = post_nodes.tolist()
                # cannot use CollocatedSynapses with a list of weight and delay
                # so loop over the syn_specs
                for syn_spec in self.get_syn_specs(cs, pre_locs, post_locs, take):
                    ssw = {**syn_spec}
                    # The weight of a collapsed pair is the sum of the connections it
                    # stands for, whether it came from a constant or was computed.
                    weight = ssw["weight"]
                    ssw["weight"] = (
                        np.asarray(weight) * multiplicity
                        if isinstance(weight, np.ndarray)
                        else [weight * m for m in multiplicity]
                    )
                    for name, value in ssw.items():
                        if name not in ("weight", "synapse_model") and not isinstance(
                            value, np.ndarray | builtins.list
                        ):
                            ssw[name] = [value] * len(cell_pairs)
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

    def get_syn_specs(self, cs=None, pre_locs=None, post_locs=None, take=None):
        """
        Build one ``syn_spec`` per configured synapse.

        Every notation a synapse can be written in is collected by
        :meth:`~bsb.simulation.parameter.ParameterizedModel.get_parameters`, so this
        only has to compute each parameter and add the model's identity.

        Called without connection locations -- the ``rule`` path, where NEST decides
        the pairs itself -- only parameters that yield a single value can be honoured.
        ``take`` selects one value per unique cell pair from a per-connection result,
        since duplicate pairs are collapsed before connecting.
        """
        per_connection = cs is not None and pre_locs is not None and post_locs is not None
        specs = []
        for synapse in self.synapses:
            spec = {"synapse_model": synapse.model}
            for name, param in synapse.get_parameters().items():
                if param.is_constant:
                    spec[name] = param.compute()
                elif per_connection:
                    values = param.compute(self.simulation, cs, pre_locs, post_locs)
                    spec[name] = values if take is None else values[take]
                else:
                    raise AdapterError(
                        f"Parameter '{name}' of synapse '{synapse.model}' in "
                        f"{self.name} is computed per connection, which needs the "
                        "connections themselves. Remove the connection `rule` so BSB "
                        "connects cell by cell, or make the parameter constant."
                    )
            specs.append(spec)
        return specs
