from bsb import from_storage
import numpy as np

scaffold = from_storage("network.hdf5")
ps = scaffold.get_placement_set("cell_A")
subpopulation_1 = ps.get_labelled(["cell_A_type_1"])
subpopulation_2 = ps.get_labelled(["cell_A_type_2"])

# or alternatively directly filter when loading the placement set
ps_1 = scaffold.get_placement_set("cell_A", labels=["cell_A_type_1"])
ps_2 = scaffold.get_placement_set("cell_A", labels=["cell_A_type_2"])

# check that the labeling was correctly positions along the axis chosen
axis = 0  # corresponds to the default value
positions_type1 = ps_1.load_positions()
positions_type2 = ps_2.load_positions()
print(
    f"{len(positions_type1)} cells were labeled as type 1, "
    f"up to {np.max(positions_type1[:, axis])} along axis {axis}"
)
print(
    f"{len(positions_type2)} cells were labeled as type 2, "
    f"starting from {np.min(positions_type2[:, axis])} along axis {axis}"
)
