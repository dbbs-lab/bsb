# The Brain Scaffold Builder

![Build Status](https://github.com/dbbs-lab/bsb/actions/workflows/main.yml/badge.svg)
[![codecov](https://codecov.io/gh/dbbs-lab/bsb/graph/badge.svg?token=9b20cUHwzX)](https://codecov.io/gh/dbbs-lab/bsb)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

Developed by the Department of Brain and Behavioral Sciences at the University of Pavia, the Brain Scaffold Builder (
BSB) is a component framework for neural modeling. It emphasizes modular component declarations to assemble brain
models, supporting various configuration languages and Python library functions. BSB facilitates parallel reconstruction
and simulation of diverse network topologies, placements, and connectivity strategies.

## Monorepo Structure

The BSB suite is now organized as a monorepo, integrating the following components:

* **bsb-core**: The foundational framework of BSB.
* **bsb-hdf5**: Storage engine for saving models in HDF5 format.
* **bsb-json**: Parser for reading and writing JSON configuration files.
* **bsb-yaml**: Parser for reading and writing YAML configuration files.
* **bsb-nest**: Simulation interface for point-neuron networks using the NEST simulator.
* **bsb-neuron**: Simulation interface for detailed neuron networks using the NEURON simulator.
* **bsb-arbor**: Simulation interface for detailed neuron networks using the ARBOR simulator.
* **nmodl-glia**: An NMODL asset manager.
* **nrn-patch**: Utility layer to reduce friction when working with NEURON in Python.
* **arborize**: Tool for Arbor-like descriptions of cell models for NEURON and Arbor.
* **bsb-test**: Tools and configurations for testing BSB components.
* **sphinxext-bsb**: Sphinx extension for BSB documentation.

## Documentation

Comprehensive documentation is available at:

* [BSB Documentation](https://bsb.readthedocs.io/en/latest)

## Installation

### Pip installation

The BSB supports Python 3.10 and above. To install the BSB suite along with the core framework and default plugins:

```bash
pip install bsb
```

For advanced users desiring a custom combination of plugins, install `bsb-core` and the desired plugins separately:

```bash
pip install bsb-core
pip install bsb-hdf5 bsb-json bsb-yaml
```

To include simulation support for NEST, NEURON, or ARBOR:

```bash
pip install bsb[nest]
pip install bsb[neuron]
pip install bsb[arbor]
```

### Clone installation

You can also clone the repository and use the devtools script to install all packages in editable mode 
in your own environment:

```bash
git clone https://github.com/dbbs-lab/bsb
cd bsb
pip install -r devtools/editable-install.txt
```

### Developer installation

For development purposes, you should install the [UV](https://docs.astral.sh/uv/) and [NX](https://nx.dev/) tools.
To this end, there is a helper script for each platform in ``devtools/bootstrap-*``. For instance, for linux:

```bash
git clone https://github.com/dbbs-lab/bsb
cd bsb
./devtools/bootstrap-linux.sh
```


From there, you NX and UV will automatically create an environment for each subpackage, 
including all necessary libraries for running the unittests, linting the code and building the documentation.

For more information, please refer to the [developers' documentation](https://bsb.readthedocs.io/en/latest/dev/dev-toc.html).

## Usage

To create a new BSB project:

```bash
bsb new my_model --quickstart
cd my_model
```

This command generates a `my_model` directory with starter files:

* `network_configuration.yaml`: Defines the network configuration.
* `pyproject.toml`: Contains project metadata and configuration.
* `placement.py` and `connectome.py`: Custom components for network placement and connectivity.

To compile the network:

```bash
bsb compile
```

For simulation, refer to the documentation for configuring simulations with NEST, NEURON, or ARBOR.

## Contributing

All contributions are very much welcome.
Take a look at the [contribution guide](CONTRIBUTING.md)

## Acknowledgements

This research has received funding from the European Union’s Horizon 2020 Framework Program for Research and Innovation
under the Specific Grant Agreements No. 945539 (Human Brain Project SGA3) and No. 785907 (Human Brain Project SGA2), as
well as from the Centro Fermi project “Local Neuronal Microcircuits” to ED. The project also receives funding from the
Virtual Brain Twin Project under the European Union's Horizon Europe program under grant agreement No. 101137289.

We acknowledge the use of the EBRAINS platform and Fenix Infrastructure resources, which are partially funded by the
European Union’s Horizon 2020 research and innovation program under the Specific Grant Agreement No. 101147319 (EBRAINS
2.0 Project) and through the ICEI project under grant agreement No. 800858, respectively.

## Supported by

[![JetBrains logo](https://resources.jetbrains.com/storage/products/company/brand/logos/jetbrains.svg)](https://jb.gg/OpenSourceSupport)
