from bsb import read_results

# Read the results together with the network they were simulated on
results = read_results(
    "my_network.hdf5",
    "simulation-results/neuronsimulation.nio",  # adapt the name of the file here
)

# Gather the recordings of each recorder, to draw one plot per device
recorders = {}
for recording in results.recordings():
    recorders.setdefault(recording.device, []).append(recording)

import matplotlib.pylab as plt  # you might have to pip install matplotlib

for name_device, recordings in recorders.items():
    # Plot only the first recording of each recorder.
    signal = recordings[0].signal
    annotations = recordings[0].annotations
    # If the signal comes from a synapse recorder
    if name_device == "synapses_rec":
        cell_id = annotations["bsb_post_cell_id"]  # The cell the synapse is on
        synapse_type = annotations["bsb_synapse_type"]
        out_filename = (
            f"simulation-results/synapses_rec_{str(cell_id)}_{synapse_type}.png"
        )
    # If the signal comes from a voltage recorder
    elif name_device == "vrecorder":
        out_filename = f"simulation-results/vrecorder_{annotations['bsb_cell_id']}.png"
    else:
        continue
    # Plot and save figure to file in results folder
    plt.figure()
    plt.xlabel(f"Time ({signal.times.units.dimensionality.string})")
    plt.ylabel(f"{signal.units.dimensionality.string}")
    plt.plot(signal.times, signal.magnitude)
    plt.savefig(out_filename, dpi=200)
