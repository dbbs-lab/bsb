from arborize import define_model

empty = define_model({})
pas = define_model(
    {
        "cable_types": {
            "soma": {
                "cable": {"Ra": 10, "cm": 1},
                "mechanisms": {"pas": {"e": -70, "g": 0.01}},
                "ions": {"ca": {"rev_pot": 10, "int_con": 10, "ext_con": 10}},
            },
            "apical_dendrite": {
                "cable": {"Ra": 10, "cm": 1},
            },
            "basal_dendrite": {
                "cable": {"Ra": 10, "cm": 1},
            },
        }
    }
)
expsyn = define_model(
    {
        "cable_types": {
            "soma": {
                "cable": {"Ra": 10, "cm": 1},
                "synapses": {"ExpSyn": {"tau": 2}},
            },
        },
        "synapse_types": {"expsyn2": {"mechanism": "ExpSyn", "parameters": {"tau": 3}}},
    },
    use_defaults=True,
)
hh_soma = define_model(
    {
        "cable_types": {
            "soma": {
                "cable": {"Ra": 10, "cm": 1},
                "mechanisms": {"pas": {}, "hh": {}},
            }
        }
    }
)
