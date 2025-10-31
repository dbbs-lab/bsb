import numpy as np

from bsb import parse_morphology_file

# Import a morphology from a file
morpho = parse_morphology_file("data/neuron_A.swc")
print(f"My morphology has {len(morpho)} points and {len(morpho.branches)} branches.")

from bsb import Storage

# Store it in a MorphologyRepository to use it later.
store = Storage("hdf5", "morphologies.hdf5")
store.morphologies.save("my_morphology", morpho)

from bsb import from_storage

# Load the morphology from the Scaffold object
scaffold = from_storage("morphologies.hdf5")
morpho = scaffold.morphologies.load("my_morphology")

# Take a branch
special_branch = morpho.branches[3]
# Assign some labels to the whole branch
special_branch.label(["axon", "special"])
# Assign labels only to the first quarter of the branch
first_quarter = np.arange(len(special_branch)) < len(special_branch) / 4
special_branch.label(["initial_segment"], first_quarter)
# Assign random data as the `random_data` property to the branch
special_branch.set_properties(random_data=np.random.random(len(special_branch)))
print(f"Random data for each point: {special_branch.random_data}")

scaffold.morphologies.save("processed_morphology", morpho)

# Filter branches
big_branches = [b for b in morpho.branches if np.any(b.radii > 2)]
for b in big_branches:
    # Label all points on the branch as a `big_branch` point
    b.label(["big_branch"])
    if b.is_terminal:
        # Label the last point on terminal branches as a `tip`
        b.label(["tip"], [-1])

scaffold.morphologies.save("labelled_morphology", morpho)
