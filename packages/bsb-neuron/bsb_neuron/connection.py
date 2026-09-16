import dataclasses
import typing

import numpy as np
from bsb import AdapterError, ConnectionModel, config, types

from bsb_neuron._util import ignore_arborize_proxy_warnings


@config.dynamic(
    attr_name="model_strategy",
    required=False,
    default="transceiver",
    auto_classmap=True,
)
class NeuronConnection(ConnectionModel):
    """
    Class interfacing a NEURON connection.
    """

    model_strategy: str
    """The strategy for neuron connection creation (e.g., 'transceiver')."""

    def create_connections(self, simulation, simdata, connections):
        """
        Connect all the cell models with the defined connection models
        for the provided connectivity set.

        :type simulation: bsb_neuron.simulation.NeuronSimulation
        :type simdata: bsb_neuron.simulation.NeuronSimulationData
        :type connections: bsb.storage.interfaces.ConnectivitySet
        """
        raise NotImplementedError(
            "Cell models should implement the `create_connections` method."
        )


@config.node
class SynapseSpec:
    """
    Class interfacing a NEURON synapse model.
    """

    synapse = config.attr(type=str, required=types.shortform())
    """Name of the synapse model."""
    weight = config.attr(type=float, default=0.004)
    """Weight of the connection between the presynaptic and the postsynaptic cells."""
    delay = config.attr(type=float, default=1.0)
    """
    Delay of the transmission between the presynaptic and the postsynaptic cells, in
    milliseconds. Defaults to NEURON's own ``NetCon`` delay of 1 ms.

    The delays of a network set NEURON's ``mindelay``, which
    ``ParallelContext.set_maxstep`` requires to be strictly positive and at least one
    :attr:`~bsb_neuron.simulation.NeuronSimulation.resolution` step. A delay of 0
    therefore aborts the simulation with ``usable mindelay is 0``.
    """

    def __init__(self, synapse_name=None, /, **kwargs):
        if synapse_name is not None:
            self._synapse = synapse_name


@dataclasses.dataclass(frozen=True)
class Receiver:
    """
    A synapse a connection makes on a cell, and the connection it belongs to.
    """

    #: The transmitter gid the synapse receives from.
    gid: int
    #: The postsynaptic cell.
    cell: typing.Any
    #: Branch and point of the synapse on the postsynaptic cell.
    location: tuple[int, int]
    #: The synapse specification.
    spec: SynapseSpec
    #: The cell model of the presynaptic cell.
    pre_model: typing.Any
    #: Cell id, branch and point where the connection starts on the presynaptic cell.
    pre: tuple[int, int, int]
    #: Name of the connectivity set the connection is in.
    connectivity_set: str


@config.node
class TransceiverModel(NeuronConnection, classmap_entry="transceiver"):
    synapses = config.list(
        type=SynapseSpec,
        required=True,
    )
    """List of synapse models to use for a connection."""
    source = config.attr(type=str)
    """Source variable to assign to the connection."""

    def create_connections(
        self,
        simulation,
        simdata,
        cs,
    ):
        self.create_transmitters(simdata, cs)
        self.create_receivers(simdata, cs)

    @ignore_arborize_proxy_warnings()
    def create_transmitters(self, simdata, cs):
        """
        :type simdata: bsb_neuron.simulation.NeuronSimulationData
        :type cs: bsb.storage.interfaces.ConnectivitySet
        """
        for cm, pop in simdata.populations.items():  # noqa: B007
            if cm.cell_type == cs.pre_type:
                break
        else:
            raise AdapterError(f"No pop found for {cs.pre_type.name}")
        pre, _ = cs.load_connections().from_(simdata.chunks).all()
        transmitters = simdata.transmap[self]["transmitters"]
        locs = np.unique(pre[:, :2], axis=0)
        for loc in locs:
            gid = transmitters[tuple(loc)]
            cell = pop[loc[0]]
            # NEURON only allows 1 spike detector per branch,
            # so we insert it in the first point on the branch.
            point = (loc[1], 0)
            cell.insert_transmitter(gid, point, source=self.source)

    @ignore_arborize_proxy_warnings()
    def create_receivers(self, simdata, cs):
        """
        :type simdata: bsb_neuron.simulation.NeuronSimulationData
        :type cs: bsb.storage.interfaces.ConnectivitySet
        """
        for receiver in self.iter_receivers(simdata, cs):
            receiver.cell.insert_receiver(
                receiver.gid,
                receiver.spec.synapse,
                receiver.location,
                source=self.source,
                weight=receiver.spec.weight,
                delay=receiver.spec.delay,
            )

    def iter_receivers(self, simdata, cs):
        """
        Iterate the synapses the connectivity set makes on the cells of this rank, in
        the order :meth:`create_receivers` inserts them.

        Nothing about a synapse's connection is kept on the synapse. A device that
        needs it walks the receivers again, so that it only costs anything for the
        synapses that are recorded.

        :type simdata: bsb_neuron.simulation.NeuronSimulationData
        :type cs: bsb.storage.interfaces.ConnectivitySet
        :returns: The receivers, one per synapse.
        :rtype: typing.Iterator[Receiver]
        """
        for post_model, post_pop in simdata.populations.items():  # noqa: B007
            if post_model.cell_type == cs.post_type:
                break
        else:
            raise AdapterError(f"No pop found for {cs.pre_type.name}")
        pre_model = next(
            (cm for cm in simdata.populations if cm.cell_type == cs.pre_type), None
        )
        query = cs.load_connections().incoming().to(simdata.chunks)
        pre, post = query.all()
        # The same connections with the presynaptic cells as placement set ids, which
        # is how a synapse names the cell it receives from.
        pre_globals = query.as_globals().all()[0]
        transmitters = simdata.transmap[self]["receivers"]
        for pre_loc, pre_global, post_loc in zip(pre, pre_globals, post, strict=True):
            gid = transmitters[tuple(pre_loc[:2])]
            cell = post_pop[post_loc[0]]
            for spec in self.synapses:
                yield Receiver(
                    gid=gid,
                    cell=cell,
                    location=tuple(int(i) for i in post_loc[1:]),
                    spec=spec,
                    pre_model=pre_model,
                    pre=tuple(int(i) for i in pre_global),
                    connectivity_set=cs.tag,
                )

    def __lt__(self, other):
        try:
            return self.name < other.name
        except Exception:
            return True
