# BSB guide on manipulating morphologies

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

The configuration files in the folder `configs` named `include_morphos.[extension]` corresponds to the
configuration files you should obtain upon completing
[the BSB morphology guide](https://bsb.readthedocs.io/en/latest/getting-started/simulations/include_morphos.html).

To run the BSB reconstruction, run the following command in this folder:
```bash
bsb compile configs/include_morphos.yaml -v 3 --clear
# or
bsb compile configs/include_morphos.json -v 3 --clear
# or
python scripts/include_morphos.py
```

You should obtain a `network.hdf5` file from this reconstruction.
You can then display the morphologies of the file, following 
[this tutorial](https://bsb.readthedocs.io/en/latest/examples/plot_morpho.html).

The python script presented in this tutorial can be launched from the terminal:
```bash
python scripts/plotting_with_branch_colors.py
```
