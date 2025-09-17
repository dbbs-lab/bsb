# BSB getting started example

## Content

This folder contains the configurations and python files related to 
[the BSB getting started tutorial](https://bsb.readthedocs.io/en/latest/getting-started/getting-started_reconstruction.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `getting_started` named `getting-started.[extension]` 
corresponds to the configuration files you should obtain upon completing
[the BSB getting started tutorial](https://bsb.readthedocs.io/en/latest/getting-started/getting-started_reconstruction.html).

To run the BSB reconstruction, run the following command in this folder:
```bash
bsb compile getting_started/getting-started.yaml -v 3 --clear
# or
bsb compile getting_started/getting-started.json -v 3 --clear
# or
python getting_started/getting-started.py
```

You should obtain a `network.hdf5` file from this reconstruction.
You can then explore the content of the file, following 
[this tutorial](https://bsb.readthedocs.io/en/latest/getting-started/basics.html).

The python script presented in this tutorial can be launched from the terminal:
```bash
python getting_started/load_data.py
```
