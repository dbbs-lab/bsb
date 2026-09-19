import numpy as np
from bsb import read_results

# Read the results together with the network they were simulated on
results = read_results(
    "network.hdf5",
    "simulation-results/basal_activity.nio",  # adapt the name of the file here
)

# Gather the recordings of each spike recorder, to draw a raster per device
recorders = {}
for recording in results.recordings(kind="cell"):
    recorders.setdefault(recording.device, []).append(recording)

import matplotlib.pylab as plt  # you might have to pip install matplotlib

fig, ax = plt.subplots(
    len(recorders), sharex=True, squeeze=False, figsize=(10, len(recorders) * 6)
)
for i, (name, recordings) in enumerate(recorders.items()):
    axis = ax[i][0]
    for recording in recordings:
        spike_times = recording.signal.magnitude  # Retrieve the spike times
        # One row per cell, at the height of the cell's id in its placement set
        axis.scatter(
            spike_times, np.full(len(spike_times), recording.target.id), c=f"C{i}", s=1
        )
    units = recordings[0].signal.times.units.dimensionality.string
    axis.set_xlabel(f"Time ({units})")
    axis.set_ylabel("Cell ID")
    axis.set_title(f"Spikes from {name}")

plt.tight_layout()
plt.savefig("simulation-results/raster_plot.png", dpi=200)
