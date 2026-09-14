from bsb.simulation.results import iter_recordings
from neo import io

# Read simulation data
my_file_name = "simulation-results/neuronsimulation.nio"  # adapt the name of the file here
sim = io.NixIO(my_file_name, mode="ro")
block = sim.read_all_blocks()[0]
segment = block.segments[0]
# Recordings are per cell and carry the same annotations everywhere, so both the
# voltage and the synapse current are read the same way.
recordings = list(iter_recordings(segment))

import matplotlib.pylab as plt  # you might have to pip install matplotlib

has_plotted_neuron = False  # We will only plot one neuron recording here
has_plotted_synapse = False  # We will only plot one synapse recording here
for recording in recordings:
    # If the signal comes from a synapse recorder,
    # and if we did not plot a synapse recording yet
    if recording.device == "synapses_rec" and not has_plotted_synapse:
        synapse_type = recording.signal.annotations["synapse_type"]
        out_filename = (
            f"simulation-results/synapses_rec_{recording.cell_id}_{synapse_type}.png"
        )
        has_plotted_synapse = True
    # If the signal comes from a voltage recorder,
    # and if we did not plot a neuron recording yet
    elif recording.device == "vrecorder" and not has_plotted_neuron:
        out_filename = f"simulation-results/vrecorder_{recording.cell_id}.png"
        has_plotted_neuron = True
    # If we plotted both types of recording, we exit the loop
    elif has_plotted_neuron and has_plotted_synapse:
        break
    # We still have some plotting to do
    else:
        continue

    signal = recording.signal
    sim_time = signal.times  # Time points of simulation recording

    # Plot and save figure to file in images folder
    plt.figure()
    plt.xlabel(f"Time ({signal.times.units.dimensionality.string})")
    plt.ylabel(f"{signal.units.dimensionality.string}")
    plt.plot(sim_time, signal.magnitude)
    plt.savefig(out_filename, dpi=200)
