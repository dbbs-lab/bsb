required_plugins = []

tree = {
    "storage": {"engine": "fs"},
    "network": {"x": 100, "y": 100, "z": 50, "chunk_size": [10, 10, 10]},
    "partitions": {},
    "cell_types": {
        "A": {
            "spatial": {"count": 1},
        },
        "B": {
            "spatial": {"count": 1},
        },
        "C": {
            "spatial": {"count": 1},
        },
    },
    "placement": {
        "across_chunks": {
            "strategy": "bsb.placement.FixedPositions",
            "cell_types": ["A", "B", "C"],
            "partitions": [],
            "positions": [
                [10, 10, 10],
                [20, 10, 10],
                [30, 10, 10],
                [60, 10, 10],
                [70, 10, 10],
                [80, 10, 10],
                [10, 60, 10],
                [10, 70, 10],
                [10, 80, 10],
                [60, 60, 10],
                [70, 70, 10],
                [80, 80, 10],
            ],
        }
    },
    "connectivity": {
        "A_to_A": {
            "strategy": "bsb_test.debug.FixedConnectivity",
            "presynaptic": {"cell_types": ["A"]},
            "postsynaptic": {"cell_types": ["A"]},
            "connections": [
                [0, 0, 0, 7, 1, 0],
                [0, 0, 0, 0, 1, 0],
                [1, 0, 0, 3, 0, 0],
                [3, 1, 0, 7, 1, 0],
            ],
        },
        "A_to_B": {
            "strategy": "bsb_test.debug.FixedConnectivity",
            "presynaptic": {"cell_types": ["A"]},
            "postsynaptic": {"cell_types": ["B"]},
            "connections": [
                [0, 0, 0, 3, 0, 0],
                [0, 1, 0, 3, 0, 0],
                [3, 0, 0, 5, 0, 0],
                [3, 0, 0, 8, 0, 0],
                [5, 0, 0, 10, 0, 0],
            ],
        },
        "B_to_C": {
            "strategy": "bsb_test.debug.FixedConnectivity",
            "presynaptic": {"cell_types": ["B"]},
            "postsynaptic": {"cell_types": ["C"]},
            "connections": [
                [5, 0, 0, 9, 0, 0],
                [5, 0, 0, 10, 0, 0],
                [5, 0, 0, 11, 0, 0],
            ],
        },
        "C_to_A": {
            "strategy": "bsb_test.debug.FixedConnectivity",
            "presynaptic": {"cell_types": ["C"]},
            "postsynaptic": {"cell_types": ["A"]},
            "connections": [
                [1, 0, 0, 5, 0, 0],
                [5, 0, 0, 1, 0, 0],
                [5, 0, 0, 11, 0, 0],
            ],
        },
        "C_to_B": {
            "strategy": "bsb_test.debug.FixedConnectivity",
            "presynaptic": {"cell_types": ["C"]},
            "postsynaptic": {"cell_types": ["B"]},
            "connections": [
                [1, 0, 0, 5, 0, 0],
                [5, 0, 0, 1, 0, 0],
                [5, 0, 0, 11, 0, 0],
            ],
        },
    },
    "simulations": {},
}
