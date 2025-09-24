# BSB example on Allen Brain Atlas integration

## Content

This folder contains the configurations and python files related to 
[the BSB tutorial on the Allen Brain Atlas](https://bsb.readthedocs.io/en/latest/examples/atlas_placement.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration file in the folder `atlas_modeling` named `atlas_modeling/atlas_structure.json` 
corresponds to the configuration file described in 
[the BSB tutorial on the Allen Brain Atlas](https://bsb.readthedocs.io/en/latest/examples/atlas_placement.html).

To run the BSB reconstruction, run the following command in the `atlas_modeling` folder:
```bash
bsb compile atlas_structure.json -v 3 --clear
```
You should obtain a `allen_densities.hdf5` file from this reconstruction.

You can also learn how to manipulate the Allen Brain Region Hierarchy with the python script in the
same folder:
```bash
python atlas_structure.py
```
