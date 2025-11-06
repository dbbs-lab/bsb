import numpy as np

from bsb import AllenStructure
from voxcell import VoxelData

# For this example, we'll be looking into the declive:
struct = "DEC"
print("Structure acronym:", struct)
# Get all the IDs that are part of this structure:
ids = AllenStructure.get_structure_idset(struct)
print("Structure IDs:", ids)
# Get the boolean mask of the structure. 1's are part of the structure, 0s aren't.
mask = AllenStructure.get_structure_mask(struct)
print("The structure contains", np.sum(mask), "voxels")
# You can use this to mask other images of the brain, such as a fictitious density file:
brain_image = VoxelData.load_nrrd("my_cell_density.nrrd")
struct_image = np.where(mask, brain_image.raw, np.nan)
# Or, if you prefer an array of the values:
struct_values = brain_image[mask]
print("Average density of the structure:", np.mean(struct_values))
