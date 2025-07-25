required_plugins = ["bsb-nest"]

tree = {
    "storage": {"engine": "fs"},
    "network": {"x": 50.0, "y": 50.0, "z": 50.0, "chunk_size": 50},
    "partitions": {"any": {"type": "layer", "thickness": 50}},
    "cell_types": {
        "excitatory": {"spatial": {"radius": 1, "count": 2000}},
        "inhibitory": {"spatial": {"radius": 1, "count": 500}},
    },
    "placement": {
        "place_cells": {
            "strategy": "bsb.placement.RandomPlacement",
            "cell_types": ["excitatory", "inhibitory"],
            "partitions": ["any"],
        }
    },
    "connectivity": {
        "excitatory_to_excitatory": {
            "strategy": "bsb.connectivity.FixedIndegree",
            "indegree": 200,
            "presynaptic": {"cell_types": ["excitatory"]},
            "postsynaptic": {"cell_types": ["excitatory"]},
        },
        "excitatory_to_inhibitory": {
            "strategy": "bsb.connectivity.FixedIndegree",
            "indegree": 200,
            "presynaptic": {"cell_types": ["excitatory"]},
            "postsynaptic": {"cell_types": ["inhibitory"]},
        },
        "inhibitory_to_inhibitory": {
            "strategy": "bsb.connectivity.FixedIndegree",
            "indegree": 50,
            "presynaptic": {"cell_types": ["inhibitory"]},
            "postsynaptic": {"cell_types": ["inhibitory"]},
        },
        "inhibitory_to_excitatory": {
            "strategy": "bsb.connectivity.FixedIndegree",
            "indegree": 50,
            "presynaptic": {"cell_types": ["inhibitory"]},
            "postsynaptic": {"cell_types": ["excitatory"]},
        },
    },
    "simulations": {
        "test_nest": {
            "simulator": "nest",
            "duration": 1000,
            "resolution": 0.1,
            "cell_models": {
                "excitatory": {
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "tau_syn_ex": 0.5,
                        "tau_syn_in": 0.5,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "V_reset": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    }
                },
                "inhibitory": {
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "tau_syn_ex": 0.5,
                        "tau_syn_in": 0.5,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "V_reset": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    }
                },
            },
            "connection_models": {
                "excitatory_to_excitatory": {
                    "synapse": {"weight": 20.68015524367846, "delay": 1.5}
                },
                "excitatory_to_inhibitory": {
                    "synapse": {"weight": 20.68015524367846, "delay": 1.5}
                },
                "inhibitory_to_excitatory": {
                    "synapse": {"weight": -103.4007762183923, "delay": 1.5}
                },
                "inhibitory_to_inhibitory": {
                    "synapse": {"weight": -103.4007762183923, "delay": 1.5}
                },
            },
            "devices": {
                "pg": {
                    "device": "poisson_generator",
                    "rate": 17789.007714721884,
                    "targetting": {"strategy": "all"},
                    "weight": 20.68015524367846,
                    "delay": 1.5,
                },
                "sr_exc": {
                    "device": "spike_recorder",
                    "delay": 1,
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["excitatory"],
                        "count": 50,
                    },
                },
                "sr_inh": {
                    "device": "spike_recorder",
                    "delay": 1,
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["inhibitory"],
                        "count": 50,
                    },
                },
            },
        },
        "test_arbor": {
            "simulator": "arbor",
            "duration": 1000,
            "resolution": 0.1,
            "cell_models": {
                "excitatory": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
                "inhibitory": {
                    "model_strategy": "lif",
                    "constants": {
                        "C_m": 250,
                        "tau_m": 20,
                        "t_ref": 2.0,
                        "E_L": 0.0,
                        "E_R": 0.0,
                        "V_m": 0.0,
                        "V_th": 20,
                    },
                },
            },
            "connection_models": {
                "excitatory_to_excitatory": {"weight": 20.68015524367846, "delay": 1.5},
                "excitatory_to_inhibitory": {"weight": 20.68015524367846, "delay": 1.5},
                "inhibitory_to_excitatory": {
                    "weight": -103.4007762183923,
                    "delay": 1.5,
                },
                "inhibitory_to_inhibitory": {
                    "weight": -103.4007762183923,
                    "delay": 1.5,
                },
            },
            "devices": {
                "pg": {
                    "device": "poisson_generator",
                    "rate": 17789.007714721884,
                    "targetting": {"strategy": "all"},
                    "weight": 20.68015524367846,
                    "delay": 1.5,
                },
                "sr_exc": {
                    "device": "spike_recorder",
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["excitatory"],
                        "count": 50,
                    },
                },
                "sr_inh": {
                    "device": "spike_recorder",
                    "targetting": {
                        "strategy": "cell_model",
                        "cell_models": ["inhibitory"],
                        "count": 50,
                    },
                },
            },
        },
    },
}
