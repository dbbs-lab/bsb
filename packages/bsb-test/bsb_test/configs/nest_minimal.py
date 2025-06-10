required_plugins = ["bsb-nest"]

tree = {
    "storage": {"engine": "fs"},
    "network": {"x": 150, "y": 150, "z": 150},
    "partitions": {},
    "cell_types": {},
    "placement": {},
    "connectivity": {},
    "simulations": {
        "test": {
            "simulator": "nest",
            "duration": 10,
            "resolution": 1.0,
            "cell_models": {},
            "connection_models": {},
            "devices": {},
        }
    },
}
