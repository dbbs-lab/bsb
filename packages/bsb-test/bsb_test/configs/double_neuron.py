required_plugins = []

tree = {
    "name": "Test multiple cell types",
    "storage": {"engine": "fs"},
    "network": {"x": 100.0, "y": 50.0, "z": 100.0, "chunk_size": [50, 50, 50]},
    "partitions": {"test_layer": {"thickness": 50}},
    "cell_types": {
        "from_cell": {"spatial": {"radius": 2.5, "count": 4}},
        "to_cell": {"spatial": {"radius": 2.5, "count": 4}},
    },
    "placement": {
        "placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "cell_types": ["from_cell", "to_cell"],
            "partitions": ["test_layer"],
        }
    },
    "connectivity": {
        "connection": {
            "strategy": "bsb.connectivity.AllToAll",
            "presynaptic": {"cell_types": ["from_cell"]},
            "postsynaptic": {"cell_types": ["to_cell"]},
        }
    },
    "simulations": {},
}
