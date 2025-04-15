[![Build Status](https://github.com/dbbs-lab/bsb/actions/workflows/main.yml/badge.svg)](https://github.com/dbbs-lab/bsb/actions/workflows/main.yml)
# Brain Scaffold Builder suite
Developed by the Department of Brain and Behavioral Sciences at the University of Pavia, 
the Brain Scaffold Builder (BSB) is a component framework for neural modelling, which focuses on component 
declarations to piece together a brain model. 
The component declarations can be made in any supported configuration language, 
or using the library functions in Python. 
It offers parallel reconstruction and simulation of any network topology, placement and/or connectivity 
strategy.

BSB is decomposed into several repositories:
- [bsb-core](#bsb-core) — Install the bsb framework. Core component of the `bsb` suite.
- [bsb-hdf5](#bsb-hdf5) — Leverage the hdf5 file format to save the models.
- [bsb-json](#bsb-json) — Read and write configuration files in json format. 
- [bsb-yaml](#bsb-yaml) — Read and write configuration files in yaml format
- [bsb-nest](#bsb-nest) — Simulate brain models as point-neuron networks with the NEST simulator.
- [bsb-neuron](#bsb-neuron) — Simulate brain models as detailed neuron networks with the NEURON simulator.
- [bsb-arbor](#bsb-arbor) — Simulate brain models as detailed neuron networks with the ARBOR simulator.

## Installation
This repository contains the metadata for the `bsb` package.
It is highly recommended that you create a python environment before installing the `bsb` package.
BSB currently supports python 3.9, 3.10 and 3.11.
With the `bsb` package will be installed the
[bsb-core](#bsb-core) framework and the following default set of plugins:
- [bsb-hdf5](#bsb-hdf5)
- [bsb-json](#bsb-json)
- [bsb-yaml](#bsb-yaml)

You can install these python libraries with the following command:
```shell
pip install bsb
```
Check also the following sections to install the other bsb plugin.

## BSB repositories
### bsb-core

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-core),

This project contains the main `bsb` framework and is needed by all the other repositories.
It also contains tools to support parallel execution with MPI. To install this support, run the following command:
```shell
pip install bsb[parallel]
```

### bsb-hdf5

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-hdf5).

This project allows the user to save their model into the hdf5 file format. 
This plugin is installed by default with the `bsb` package.

### bsb-json

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-json).

This project allows the user to write their model configuration in the json file format. 
This plugin is installed by default with the `bsb` package.

### bsb-yaml

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-yaml).

This project allows the user to write their model configuration in the yaml file format. 
This plugin is installed by default with the `bsb` package.

### bsb-nest

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-nest).

This project allows the user to simulate their brain model as point-neuron networks with the 
[NEST simulator](https://www.nest-simulator.org/).
This plugin is not installed by default with the `bsb` package. To install it, you can run the following command:

```shell
pip install bsb[nest]
```
> [!WARNING]
> The NEST simulator is not installed with the bsb-nest package and should be installed separately.

### bsb-neuron

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-neuron).

This project allows the user to simulate their brain model as detailed neural circuits with the 
[NEURON simulator](https://www.neuron.yale.edu/neuron/).
This plugin is not installed by default with the `bsb` package. To install it, you can run the following command:
```shell
pip install bsb[neuron]
```

### bsb-arbor

Useful links:
[GitHub repo](https://github.com/dbbs-lab/bsb-arbor).

This project allows the user to simulate their brain model as detailed neural circuits with the 
[ARBOR simulator](https://arbor-sim.org/).
This plugin is not installed by default with the `bsb` package. To install it, you can run the following command:
```shell
pip install bsb[arbor]
```

## Running bsb reconstructions and simulations
Check BSB [Documentation](https://bsb.readthedocs.io/en/latest).

## Acknowledgements

This research has received funding from the European Union’s Horizon 2020 Framework
Program for Research and Innovation under the Specific Grant Agreement No. 945539
(Human Brain Project SGA3) and Specific Grant Agreement No. 785907 (Human Brain
Project SGA2) and from Centro Fermi project “Local Neuronal Microcircuits” to ED. 
The project is also receiving funding from the Virtual Brain Twin Project under the 
European Union's Research and Innovation Program Horizon Europe under grant agreement 
No 101137289. 

We acknowledge the use of EBRAINS platform and Fenix Infrastructure resources, which are
partially funded from the European Union’s Horizon 2020 research and innovation
programme under the Specific Grant Agreement No. 101147319 (EBRAINS 2.0 Project) and 
through the ICEI project under the grant agreement No. 800858 respectively.

### Supported by

[![JetBrains logo](https://resources.jetbrains.com/storage/products/company/brand/logos/jetbrains.svg)](https://jb.gg/OpenSourceSupport)
