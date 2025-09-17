# BSB example on component writing

## Content

This folder contains the configurations and python files related to 
[the BSB tutorial on writing components](https://bsb.readthedocs.io/en/latest/getting-started/guide_components.html).

## Installation 

This example is supported on Python 3.10 and above. 
To install the required Python libraries, run the following command in this folder:
```bash
pip install -e.
```

## Usage

The configuration files in the folder `writing_components` named `writing_components/writing_components.[extension]` 
corresponds to the configuration files you should obtain upon completing
[the BSB tutorial on writing components](https://bsb.readthedocs.io/en/latest/getting-started/guide_components.html).

To run the BSB reconstruction, run the following command in this folder:
```bash
bsb compile writing_components/writing_components.yaml -v 3 --clear
# or
bsb compile writing_components/writing_components.json -v 3 --clear
# or
python writing_components/writing_components.py
```

You should obtain a `network.hdf5` file from this reconstruction.
