import bsb.options
from bsb import Configuration, Scaffold

bsb.options.verbosity = 3
config = Configuration.default(storage={"engine": "hdf5", "root": "network.hdf5"})

config.network.x = 200.0
config.network.y = 200.0
config.network.z = 200.0

config.partitions.add("base_layer", thickness=100)
config.regions.add(
    "brain_region",
    type="stack",
    children=[
        "base_layer",
    ],
)

config.cell_types.add(
    "cell_A",
    spatial=dict(
        radius=2.5,
        density=3.9e-4,
    ),
)

config.placement.add(
    "base_placement",
    strategy="bsb.placement.RandomPlacement",
    cell_types=["cell_A"],
    partitions=["base_layer"],
)

config.after_placement.add(
    "Labels",
    strategy="cell_labeling.label_cells.LabelCellA",
    cell_type="cell_A",
)

scaffold = Scaffold(config)
scaffold.compile(clear=True)
