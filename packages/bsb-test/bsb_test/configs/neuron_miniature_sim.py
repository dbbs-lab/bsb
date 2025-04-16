required_plugins = ["bsb-neuron"]

tree = {
    "name": "Test miniature NEURON network",
    "storage": {"engine": "fs", "root": "nrn_miniature.hdf5"},
    "network": {"x": 150.0, "y": 600, "z": 150.0},
    "regions": {"cerebellar_cortex": {"children": ["test_layer"]}},
    "partitions": {"test_layer": {"thickness": 600, "z_index": 0}},
    "cell_types": {
        "golgi_cell": {
            "spatial": {"radius": 2.5, "count": 3},
            "plotting": {"display_name": "Golgi cell", "color": "#E62214"},
        },
        "purkinje_cell": {
            "spatial": {"radius": 2.5, "count": 2},
            "plotting": {"display_name": "Purkinje cell", "color": "#E62214"},
        },
        "stellate_cell": {
            "spatial": {"radius": 2.5, "count": 2},
            "plotting": {"display_name": "Stellate cell", "color": "#E62214"},
        },
    },
    "placement": {
        "granular_layer_placement": {
            "strategy": "bsb.placement.FixedPositions",
            "partitions": ["test_layer"],
            "cell_types": ["golgi_cell"],
            "positions": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        },
        "purkinje_layer_placement": {
            "strategy": "bsb.placement.FixedPositions",
            "partitions": ["test_layer"],
            "cell_types": ["purkinje_cell"],
            "positions": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        },
        "molecular_layer_placement": {
            "strategy": "bsb.placement.FixedPositions",
            "partitions": ["test_layer"],
            "cell_types": ["stellate_cell"],
            "positions": [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
        },
    },
    "connectivity": {},
    "simulations": {
        "test": {
            "simulator": "neuron",
            "duration": 500,
            "temperature": 32,
            "resolution": 0.025,
            "cell_models": {
                "golgi_cell": {
                    "model": "dbbs_models.GolgiCell",
                    "record_soma": True,
                    "record_spikes": True,
                },
                "purkinje_cell": {
                    "model": "dbbs_models.PurkinjeCell",
                    "record_soma": True,
                    "record_spikes": True,
                },
                "stellate_cell": {
                    "model": "dbbs_models.StellateCell",
                    "record_soma": True,
                    "record_spikes": True,
                },
            },
            "connection_models": {
                "gap_goc": {"synapses": ["gap"], "source": "vgap"},
                "stellate_to_purkinje": {"synapses": ["GABA"]},
            },
            "devices": {
                "periodic_spike_generator": {
                    "io": "input",
                    "device": "spike_generator",
                    "targetting": "cell_type",
                    "cell_types": ["golgi_cell"],
                    "cell_fraction": 1,
                    "section_types": ["basal_dendrites"],
                    "synapses": ["AMPA_AA", "NMDA"],
                    "section_count": 5,
                    "record": True,
                    "parameters": {
                        "noise": False,
                        "start": 100,
                        "interval": 5,
                        "number": 20,
                        "sd": 5,
                    },
                },
                "noisy_spike_generator": {
                    "io": "input",
                    "device": "spike_generator",
                    "targetting": "cell_type",
                    "cell_types": ["golgi_cell"],
                    "cell_fraction": 1,
                    "section_types": ["basal_dendrites"],
                    "synapses": ["AMPA_AA", "NMDA"],
                    "section_count": 5,
                    "record": True,
                    "parameters": {
                        "noise": True,
                        "start": 100,
                        "interval": 5,
                        "number": 20,
                        "sd": 5,
                    },
                },
                "fixed_spike_generator": {
                    "io": "input",
                    "device": "spike_generator",
                    "targetting": "cell_type",
                    "cell_types": ["golgi_cell"],
                    "cell_fraction": 1,
                    "section_types": ["basal_dendrites"],
                    "synapses": ["AMPA_AA", "NMDA"],
                    "section_count": 5,
                    "record": True,
                    "spike_times": [100, 102, 104, 108],
                },
                "dendrite_recorders": {
                    "io": "output",
                    "device": "voltage_recorder",
                    "group": "dendrites",
                    "targetting": "representatives",
                    "section_types": ["dendrites"],
                    "section_count": 5,
                },
            },
        }
    },
}
