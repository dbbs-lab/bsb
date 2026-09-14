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

fig, ax = plt.subplots(len(devices), sharex=True, figsize=(10, len(devices) * 6))
for i, (name, recordings) in enumerate(devices.items()):
    for recording in recordings:
        spike_times = recording.signal.magnitude  # Retrieve the spike times
        # One row per cell, at the height of the id the recording belongs to
        row = recording.cell_id or 0
        ax[i].scatter(
            spike_times, np.full(len(spike_times), row), c=f"C{i}"
        )
    units = recordings[0].signal.times.units.dimensionality.string
    ax[i].set_xlabel(f"Time ({units})")
    ax[i].set_ylabel("Neuron ID")
    ax[i].set_title(f"Spikes from {name}")
plt.tight_layout()
plt.savefig("simulation-results/raster_plot.png", dpi=200)
