# Load and display a morphology from a compiled network
import numpy as np
from matplotlib.pylab import plt

from bsb import from_storage

scaffold = from_storage("network.hdf5")
cell_type_name = "base_type"  # to which is attached the neuron_A.swc morpho
ps = scaffold.get_placement_set(cell_type_name)

# We will only display one cell here
cell_id = 14  # cell id to display
morpho = ps.load_morphologies().get(cell_id)
rotation = ps.load_rotations()[cell_id]
offset_position = ps.load_positions()[cell_id]

# Rotate, translate morphology
morpho.rotate(rotation)
morpho.translate(offset_position)

# Example of 3D display with matplotlib
fig = plt.figure(figsize=(10, 10))
ax1 = fig.add_subplot(111, projection="3d")
for branch in morpho.branches:
    x, z, y = branch.points.T
    # filter labels to use a different color for dendrites and axons
    is_axon = np.array(
        [
            np.isin(list(branch.labelsets[branch.labels[i]]), ["axon"]).any()
            for i in range(len(branch.points))
        ]
    )
    (dendrite,) = ax1.plot(x[~is_axon], y[~is_axon], z[~is_axon], c="blue")
    (axon,) = ax1.plot(x[is_axon], y[is_axon], z[is_axon], c="red")
ax1.set_xlabel("x [µm]")
ax1.set_ylabel("y [µm]")
ax1.set_zlabel("z [µm]")
if len(morpho.branches) > 0:
    ax1.legend([dendrite, axon], ["dendrites", "axon"])
# plt.show()
fig.savefig("cell_morphology.png", dpi=200)
