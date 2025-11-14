# BSB guide on labeling cells in your circuit

## Content

This folder contains the configurations and python files related to 
[the BSB cell labeling guide](https://bsb.readthedocs.io/en/latest/examples/label_cells.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `configs` named `cell_labeling.[extension]` corresponds to the
configuration files you should obtain upon completing
[the BSB cell labeling guide](https://bsb.readthedocs.io/en/latest/examples/label_cells.html).

To run the BSB reconstruction, run the following command in this folder:
```bash
bsb compile configs/cell_labeling.yaml -v 3 --clear
# or
bsb compile configs/cell_labeling.json -v 3 --clear
# or
python scripts/cell_labeling.py
```

You should obtain a `network.hdf5` file from this reconstruction.

The results of this reconstruction can be tested with the python script presented in this tutorial.
It can be launched from the terminal:
```bash
python script/test_labels.py
```