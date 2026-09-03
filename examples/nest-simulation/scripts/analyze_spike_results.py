import numpy as np
from bsb.simulation.results import iter_recordings
from neo import io

# Read simulation data
my_file_name = "simulation-results/basal_activity.nio"  # adapt the name of the file here
sim = io.NixIO(my_file_name, mode="ro")
block = sim.read_all_blocks()[0]
segment = block.segments[0]

# Spikes are recorded one train per cell, so gather each device's cells back together
# to plot a device as one raster. Cells that never fired have no train at all.
devices = {}
for recording in iter_recordings(segment):
    devices.setdefault(recording.device, []).append(recording)

import matplotlib.pylab as plt  # you might have to pip install matplotlib

fig, ax = plt.subplots(
    len(devices), sharex=True, squeeze=False, figsize=(10, len(devices) * 6)
)
for i, (name, recordings) in enumerate(devices.items()):
    axis = ax[i][0]
    for recording in recordings:
        spike_times = recording.signal.magnitude  # Retrieve the spike times
        # One row per cell, at the height of the id the recording belongs to
        axis.scatter(
            spike_times, np.full(len(spike_times), recording.cell_id), c=f"C{i}", s=1
        )
    units = recordings[0].signal.times.units.dimensionality.string
    axis.set_xlabel(f"Time ({units})")
    axis.set_ylabel("Neuron ID")
    axis.set_title(f"Spikes from {name}")
plt.tight_layout()
plt.savefig("simulation-results/raster_plot.png", dpi=200)
