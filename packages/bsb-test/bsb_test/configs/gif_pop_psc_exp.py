required_plugins = ["bsb-nest"]

tree = {
    "storage": {"engine": "fs"},
    "network": {"x": 50.0, "y": 50.0, "z": 50.0, "chunk_size": 50},
    "partitions": {"any": {"type": "layer", "thickness": 50}},
    "cell_types": {"gif_pop_psc_exp": {"spatial": {"radius": 1, "count": 1}}},
    "placement": {
        "place_cells": {
            "strategy": "bsb.placement.RandomPlacement",
            "cell_types": ["gif_pop_psc_exp"],
            "partitions": ["any"],
        }
    },
    "connectivity": {
        "gif_pop_psc_exp": {
            "strategy": "bsb.connectivity.AllToAll",
            "presynaptic": {"cell_types": ["gif_pop_psc_exp"]},
            "postsynaptic": {"cell_types": ["gif_pop_psc_exp"]},
        }
    },
    "simulations": {
        "test_nest": {
            "simulator": "nest",
            "duration": 10000,
            "resolution": 1.0,
            "cell_models": {
                "gif_pop_psc_exp": {
                    "model": "gif_pop_psc_exp",
                    "constants": {
                        "V_reset": 0.0,
                        "V_T_star": 10.0,
                        "E_L": 0.0,
                        "Delta_V": 2.0,
                        "C_m": 250.0,
                        "tau_m": 20.0,
                        "t_ref": 4.0,
                        "I_e": 500.0,
                        "lambda_0": 10.0,
                        "tau_syn_in": 2.0,
                        "tau_sfa": [500.0],
                        "q_sfa": [1.0],
                    },
                }
            },
            "connection_models": {
                "gif_pop_psc_exp": {
                    "rule": "all_to_all",
                    "synapse": {"weight": -6.25, "delay": 1},
                }
            },
            "devices": {},
        }
    },
}
