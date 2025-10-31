from bsb_nest import NestAdapter

from bsb import from_storage

scaffold = from_storage("network.hdf5")
simulation = scaffold.get_simulation("basal_activity")
adapter = NestAdapter()

nb_repetitions = 10

for i in range(nb_repetitions):
    # Set the stimulation rate on the `general_noise` device
    input_rate = i * 10.0
    simulation.devices["general_noise"].rate = input_rate
    # Clear NEST
    adapter.reset_kernel()
    # Let the adapter translate the simulation config into
    # simulator specific instructions
    simulation_backend = adapter.prepare(simulation)
    # You have free access to the `simulation_backend` here, to tweak
    # or augment the framework's instructions.

    # ...

    # Let the adapter run the simulation and collect the output.
    results = adapter.run(simulation)
    results = adapter.collect(results)
    results = results[0]  # here we only run one simulation
    # Organize the Neo data file into your data workflow by tagging it,
    # renaming it, moving it, giving it metadata, ...
    output_file = f"simulation-results/my_simulation_results_{input_rate}Hz.nio"
    results.write(output_file, "ow")
