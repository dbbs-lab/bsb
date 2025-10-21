# BSB guides on point-neuron simulations

## Content

This folder contains the configurations and python files related to 
[the BSB NEST guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/guide_nest.html).

## Installation 

This example is supported on Python 3.10 and above. 
You would need to install the NEST simulator, following 
[these instructions](https://nest-simulator.readthedocs.io/en/stable/installation/index.html). 

To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `configs` named `guide_nest.[extension]`
corresponds to the configuration files you should obtain upon completing
[the BSB NEST guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/guide_nest.html).

To run the BSB reconstruction and simulation, run the following command in this folder:
```bash
bsb compile configs/guide_nest.yaml -v 3 --clear
bsb simulate network.hdf5 basal_activity -o simulation-results
# or
bsb compile configs/guide_nest.json -v 3 --clear
bsb simulate network.hdf5 basal_activity -o simulation-results
# or
python scripts/guide_nest.py
```

You should obtain a `network.hdf5` file from this reconstruction and the results of the 
NEST simulation should appear in a `simulation-results` folder.
You can then extract NEST simulation results, following 
[this tutorial](https://bsb.readthedocs.io/en/latest/getting-started/simulations/analyze_spikes.html).

The python script presented in this tutorial can be launched from the terminal:
```bash
python scripts/analyze_spike_results.py
```
Note that you might need to adapt it to your simulation output files.