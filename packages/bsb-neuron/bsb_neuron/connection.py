import numpy as np
from bsb import AdapterError, ConnectionModel, Parameter, config, types


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
    delay = config.attr(type=float, default=0.0)
    """Delay of the transmission between the presynaptic and the postsynaptic cells."""
    parameters = config.list(type=Parameter)
    """List of parameters to assign to the synapse model."""

    def __init__(self, synapse_name=None, /, **kwargs):
        if synapse_name is not None:
            self._synapse = synapse_name


@config.node
class TransceiverModel(NeuronConnection, classmap_entry="transceiver"):
    synapses = config.list(
        type=SynapseSpec,
        required=True,
    )
    """List of synapse models to use for a connection."""
    parameters = config.list(type=Parameter)
    """List of parameters to assign to the connection."""
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

    def create_receivers(self, simdata, cs):
        """
        :type simdata: bsb_neuron.simulation.NeuronSimulationData
        :type cs: bsb.storage.interfaces.ConnectivitySet
        """
        for post_cm, post_pop in simdata.populations.items():  # noqa: B007
            if post_cm.cell_type == cs.post_type:
                break
        else:
            raise AdapterError(f"No pop found for {cs.pre_type.name}")
        pre, post = cs.load_connections().incoming().to(simdata.chunks).all()
        transmitters = simdata.transmap[self]["receivers"]
        for pre_loc, post_loc in zip(pre[:, :2], post, strict=False):
            gid = transmitters[tuple(pre_loc)]
            cell = post_pop[post_loc[0]]
            for spec in self.synapses:
                cell.insert_receiver(
                    gid,
                    spec.synapse,
                    post_loc[1:],
                    source=self.source,
                    weight=spec.weight,
                    delay=spec.delay,
                )

    def __lt__(self, other):
        try:
            return self.name < other.name
        except Exception:
            return True
