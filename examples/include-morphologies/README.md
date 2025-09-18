# BSB guide on adding morphologies to your circuit

## Content

This folder contains the configurations and python files related to 
[the BSB morphology guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/include_morphos.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `include_morphologies` named `include_morphos.[extension]` corresponds to the
configuration files you should obtain upon completing
[the BSB morphology guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/include_morphos.html).
To run the BSB reconstruction, run the following command in this folder:
```bash
bsb compile include_morphologies/include_morphos.yaml -v 3 --clear
# or
bsb compile include_morphologies/include_morphos.json -v 3 --clear
# or
python include_morphologies/include_morphos.py
```

You should obtain a `network.hdf5` file from this reconstruction.
You can then display the morphologies of the file, following 
[this tutorial](https://bsb.readthedocs.io/en/latest/examples/plot_morpho.html).

The python script presented in this tutorial can be launched from the terminal:
```bash
python getting_started/plotting_with_branch_colors.py
```
