required_plugins = []

tree = {
    "name": "Test config v4",
    "storage": {"engine": "fs"},
    "network": {"x": 400.0, "y": 400.0, "z": 400.0},
    "regions": {
        "some_brain": {"type": "stack", "children": ["some_cortex", "some_olive"]},
        "some_cortex": {
            "type": "stack",
            "children": [
                "dcn_layer",
                "granular_layer",
                "purkinje_layer",
                "b_molecular_layer",
                "t_molecular_layer",
            ],
        },
        "some_olive": {"type": "stack", "children": ["io_layer"]},
    },
    "partitions": {
        "dcn_layer": {"thickness": 600.0},
        "granular_layer": {"thickness": 150.0},
        "purkinje_layer": {"thickness": 30.0},
        "b_molecular_layer": {"thickness": 50.0},
        "t_molecular_layer": {"thickness": 100.0},
        "io_layer": {"thickness": 15.0},
    },
    "cell_types": {
        "granule_cell": {
            "spatial": {
                "radius": 2.5,
                "density": 3.9e-3,
                "geometry": {"pf_height": 126, "pf_height_sd": 15},
            },
            "plotting": {
                "display_name": "Granule cell",
                "color": "#e81005",
                "opacity": 0.3,
            },
        },
        "mossy_fibers": {
            "entity": True,
            "spatial": {"relative_to": "glomerulus", "count_ratio": 0.05},
        },
        "glomerulus": {
            "spatial": {"radius": 1.5, "density": 3e-4},
            "plotting": {"display_name": "Glomerulus", "color": "#6F6F70"},
        },
        "purkinje_cell": {
            "spatial": {"radius": 7.5, "planar_density": 0.0017},
            "plotting": {"display_name": "Purkinje cell", "color": "#068f0d"},
        },
        "golgi_cell": {
            "spatial": {"radius": 8.0, "density": 9e-6},
            "plotting": {"display_name": "Golgi cell", "color": "#1009e3"},
        },
        "stellate_cell": {
            "spatial": {"radius": 4.0, "density": 0.5e-4},
            "plotting": {"display_name": "Stellate cell", "color": "#f5bb1d"},
        },
        "basket_cell": {
            "spatial": {"radius": 6.0, "density": 0.5e-4},
            "plotting": {"display_name": "Basket cell", "color": "#f5830a"},
        },
        "dcn_cell": {
            "spatial": {
                "radius": 10.0,
                "relative_to": "purkinje_cell",
                "count_ratio": 0.090909,
            },
            "plotting": {"display_name": "DCN cell", "color": "#080808"},
        },
        "dcn_interneuron": {
            "spatial": {"radius": 6.0},
            "plotting": {"display_name": "DCN interneuron", "color": "#260582"},
        },
        "io_cell": {
            "spatial": {"radius": 7.5, "density": 1.52e-5},
            "plotting": {"display_name": "io cell", "color": "#7d1bbf"},
        },
    },
    "placement": {
        "granular_layer_innervation": {
            "strategy": "bsb.placement.Entities",
            "partitions": ["granular_layer"],
            "cell_types": ["mossy_fibers"],
        },
        "granular_layer_placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "partitions": ["granular_layer"],
            "cell_types": ["granule_cell", "golgi_cell", "glomerulus"],
        },
        "purkinje_layer_placement": {
            "strategy": "bsb.placement.ParallelArrayPlacement",
            "partitions": ["purkinje_layer"],
            "cell_types": ["purkinje_cell"],
            "spacing_x": 130.0,
            "angle": 70.0,
        },
        "b_molecular_layer_placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "partitions": ["b_molecular_layer"],
            "cell_types": ["basket_cell"],
        },
        "t_molecular_layer_placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "partitions": ["t_molecular_layer"],
            "cell_types": ["stellate_cell"],
        },
        "dcn_placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "partitions": ["dcn_layer"],
            "cell_types": ["dcn_cell"],
        },
        "io_layer_placement": {
            "strategy": "bsb.placement.RandomPlacement",
            "partitions": ["io_layer"],
            "cell_types": ["io_cell"],
        },
    },
    "connectivity": {
        "io_to_dcn": {
            "strategy": "bsb.connectivity.AllToAll",
            "presynaptic": {
                "cell_types": ["io_cell"],
                "morphology_labels": ["axon"],
                "labels": ["microzone-*"],
            },
            "postsynaptic": {
                "cell_types": ["dcn_cell"],
                "morphology_labels": ["dendrites"],
                "labels": ["microzone-*"],
            },
        }
    },
    "after_placement": {},
    "simulations": {},
}
