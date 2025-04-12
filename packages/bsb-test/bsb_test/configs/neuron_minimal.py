required_plugins = ["bsb-neuron"]

tree = {
    "storage": {"engine": "fs"},
    "network": {"x": 150, "y": 150, "z": 150},
    "partitions": {},
    "cell_types": {},
    "placement": {},
    "connectivity": {},
    "simulations": {
        "test": {
            "simulator": "neuron",
            "temperature": 32,
            "duration": 10,
            "cell_models": {},
            "connection_models": {},
            "devices": {},
        }
    },
}
