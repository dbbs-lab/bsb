import pathlib

import bsb.options
from bsb import Configuration, Scaffold

bsb.options.verbosity = 3
config = Configuration.default(
    name="Starting example",
    storage={"engine": "hdf5", "root": "network.hdf5"},
    network={"x": 200.0, "y": 200.0, "z": 200.0},
    regions={
      "brain_region": {"type": "stack", "children": ["base_layer", "top_layer"]}
    },
    partitions= {
      "base_layer": {"type": "layer", "thickness": 100},
      "top_layer": {"type": "layer", "thickness": 100}
    },
    cell_types={
      "base_type": {"spatial": {"radius": 2.5, "density": 3.9e-4}},
      "top_type": {"spatial": {"radius": 7, "count": 40}}
    },
    placement={
      "example_placement": {
        "strategy": "bsb.placement.RandomPlacement",
        "cell_types": ["base_type"],
        "partitions": ["base_layer"]
      },
      "top_placement": {
        "strategy": "bsb.placement.RandomPlacement",
        "cell_types": ["top_type"],
        "partitions": ["top_layer"]
      }
    },
    connectivity={
      "A_to_B": {
        "strategy": "bsb.connectivity.AllToAll",
        "presynaptic": {"cell_types": ["base_type"]},
        "postsynaptic": {"cell_types": ["top_type"]}
      }
    }
)

scaffold = Scaffold(config)
config = scaffold.configuration

config.simulations["basal_activity"] = dict(
    simulator="nest",
    resolution=0.1,
    duration=5000,
    cell_models={},
    connection_models={},
    devices={},
)

config.simulations["basal_activity"].cell_models = dict(
    base_type={"model": "iaf_cond_alpha"},
    top_type={"model": "iaf_cond_alpha", "constants": {"t_ref": 1.5, "V_m": -62.0}},
)

config.simulations["basal_activity"].connection_models = dict(
    A_to_B=dict(synapse=dict(model="static_synapse", weight=100, delay=1))
)

config.simulations["basal_activity"].devices = dict(
    general_noise=dict(
        device="poisson_generator",
        rate=20,
        targetting={"strategy": "cell_model", "cell_models": ["base_type"]},
        weight=40,
        delay=1,
    ),
    base_layer_record=dict(
        device="spike_recorder",
        delay=0.1,
        targetting={"strategy": "cell_model", "cell_models": ["base_type"]},
    ),
    top_layer_record=dict(
        device="spike_recorder",
        delay=0.1,
        targetting={"strategy": "cell_model", "cell_models": ["top_type"]},
    ),
)

# create the simulation results folder
root = pathlib.Path("simulation-results")
root.mkdir(exist_ok=True)
# run the simulation and save the results
result = scaffold.run_simulation("basal_activity")
result.write(root / "basal_activity.nio", "ow")
