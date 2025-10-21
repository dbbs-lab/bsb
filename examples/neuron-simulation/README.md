# BSB guides on multi-compartment neurons simulation

## Content

This folder contains the configurations and python files related to 
[the BSB NEURON guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/guide_neuron.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `configs` named `guide_neuron.[extension]`
corresponds to the configuration files you should obtain upon completing
[the BSB NEURON guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/guide_neuron.html).

To run the BSB reconstruction and simulation, run the following command in this folder:
```bash
bsb compile configs/guide_neuron.yaml -v 3 --clear
bsb simulate my_network.hdf5 neuronsim -o simulation-results
# or
bsb compile configs/guide_neuron.json -v 3 --clear
bsb simulate my_network.hdf5 neuronsim -o simulation-results
# or
python scripts/guide_neuron.py
```

You should obtain a `network.hdf5` file from this reconstruction and the results of the 
NEURON simulation should appear in a `simulation-results` folder.
You can then extract NEURON simulation results, following 
[this tutorial](https://bsb.readthedocs.io/en/latest/getting-started/simulations/analyze_analog_signals.html).

The python script presented in this tutorial can be launched from the terminal:
```bash
python scripts/analyze_analog_results.py
```
Note that you might need to adapt it to your simulation output files.