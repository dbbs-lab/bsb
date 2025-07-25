## 6.0.3 (2025-07-25)

This was a version bump only for bsb-core to align it with other projects, there were no code changes.

## 6.0.2 (2025-07-18)

### 🩹 Fixes

- nx commands ([#153](https://github.com/dbbs-lab/bsb/pull/153))

### ❤️ Thank You

- Dimitri RODARIE

## 6.0.1 (2025-07-16)

### 🩹 Fixes

- retrieve new version from update_codemeta.py for release GHA ([d8018e3](https://github.com/dbbs-lab/bsb/commit/d8018e3))
- update_codemeta.py to adapt to new location ([2f4f552](https://github.com/dbbs-lab/bsb/commit/2f4f552))
- release GHA, install mpi deps ([f206164](https://github.com/dbbs-lab/bsb/commit/f206164))
- patch documentation and gha ([#147](https://github.com/dbbs-lab/bsb/pull/147), [#144](https://github.com/dbbs-lab/bsb/issues/144), [#142](https://github.com/dbbs-lab/bsb/issues/142))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

# 6.0.0 (2025-06-11)

### 🚀 Features

- ⚠️  Integrated BSB landscape into a monorepository ([#143](https://github.com/dbbs-lab/bsb/pull/143), [#6](https://github.com/dbbs-lab/bsb/issues/6), [#3458](https://github.com/dbbs-lab/bsb/issues/3458))

### ⚠️  Breaking Changes

- ⚠️  Integrated BSB landscape into a monorepository ([#143](https://github.com/dbbs-lab/bsb/pull/143), [#6](https://github.com/dbbs-lab/bsb/issues/6), [#3458](https://github.com/dbbs-lab/bsb/issues/3458))

### ❤️ Thank You

- Robin De Schepper

## [v5.1.1] - 2025-03-28
### :bug: Bug Fixes
- [`e7635d1`](https://github.com/dbbs-lab/bsb-core/commit/e7635d19b0094b026163907b69f1b0f2a7a35425) - ref parsing when key is deep *(PR [#917](https://github.com/dbbs-lab/bsb-core/pull/917) by [@drodarie](https://github.com/drodarie))*


## [v5.1.0] - 2025-03-03
### :sparkles: New Features
- [`aa4d082`](https://github.com/dbbs-lab/bsb-core/commit/aa4d082155a76fc436b9d66de10ba4bbb0c318fe) - Expose intermediate function for parse configuration *(PR [#913](https://github.com/dbbs-lab/bsb-core/pull/913) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *addresses issue [#911](https://github.com/dbbs-lab/bsb-core/issues/911) opened by [@drodarie](https://github.com/drodarie)*


## [v5.0.2] - 2025-01-13
### :bug: Bug Fixes
- [`818de95`](https://github.com/dbbs-lab/bsb-core/commit/818de951ecfee9ae288d40044cc7b7a3456e1d44) - CLI bsb simulate command *(PR [#909](https://github.com/dbbs-lab/bsb-core/pull/909) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#908](https://github.com/dbbs-lab/bsb-core/issues/908) opened by [@drodarie](https://github.com/drodarie)*


## [v5.0.1] - 2025-01-12
### :bug: Bug Fixes
- [`0fa0711`](https://github.com/dbbs-lab/bsb-core/commit/0fa0711a0ba86ea88f5871347f6679e455d13269) - Implement feedback on new docs *(PR [#905](https://github.com/dbbs-lab/bsb-core/pull/905) by [@drodarie](https://github.com/drodarie))*


## [v5.0.0] - 2025-01-07
### :boom: BREAKING CHANGES
- due to [`575c9bd`](https://github.com/dbbs-lab/bsb-core/commit/575c9bd7289c47838efd3a5dc0b54105206ac6f5) - mpi hdf5 *(PR [#902](https://github.com/dbbs-lab/bsb-core/pull/902) by [@drodarie](https://github.com/drodarie))*:

  mpi hdf5 (#902)


### :bug: Bug Fixes
- [`553f8b3`](https://github.com/dbbs-lab/bsb-core/commit/553f8b3684f3eada58e5a351ad2005645890c9e6) - bump bsb-hdf5 version *(commit by [@drodarie](https://github.com/drodarie))*

### :recycle: Refactors
- [`575c9bd`](https://github.com/dbbs-lab/bsb-core/commit/575c9bd7289c47838efd3a5dc0b54105206ac6f5) - mpi hdf5 *(PR [#902](https://github.com/dbbs-lab/bsb-core/pull/902) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *addresses issue [#893](https://github.com/dbbs-lab/bsb-core/issues/893) opened by [@drodarie](https://github.com/drodarie)*


## [v4.5.5] - 2024-12-17
### :bug: Bug Fixes
- [`e65bdd6`](https://github.com/dbbs-lab/bsb-core/commit/e65bdd6367c1e2547cb519143ccccb593963dad4) - parallel arrays *(PR [#903](https://github.com/dbbs-lab/bsb-core/pull/903) by [@drodarie](https://github.com/drodarie))*


## [v4.5.4] - 2024-12-16
### :bug: Bug Fixes
- [`516dc63`](https://github.com/dbbs-lab/bsb-core/commit/516dc631afcb77dbbc3c90c770af20b2f129e6d9) - Update configuration to store whenever an attribute is set *(PR [#900](https://github.com/dbbs-lab/bsb-core/pull/900) by [@filimarc](https://github.com/filimarc))*
  - :arrow_lower_right: *fixes issue [#899](https://github.com/dbbs-lab/bsb-core/issues/899) opened by [@drodarie](https://github.com/drodarie)*
- [`5799cf8`](https://github.com/dbbs-lab/bsb-core/commit/5799cf848944207cbf21d7183b75c78f678bbb38) - postprocessing *(PR [#901](https://github.com/dbbs-lab/bsb-core/pull/901) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#887](https://github.com/dbbs-lab/bsb-core/issues/887) opened by [@drodarie](https://github.com/drodarie)*


## [v4.5.3] - 2024-10-29
### :bug: Bug Fixes
- [`0dac469`](https://github.com/dbbs-lab/bsb-core/commit/0dac46937c26a078b8b92864321919d8ed2ccac7) - mpi comm *(PR [#896](https://github.com/dbbs-lab/bsb-core/pull/896) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#894](https://github.com/dbbs-lab/bsb-core/issues/894) opened by [@drodarie](https://github.com/drodarie)*


## [v4.5.2] - 2024-10-12
### :bug: Bug Fixes
- [`21015c5`](https://github.com/dbbs-lab/bsb-core/commit/21015c530e340140ee424e4dbc7b18053a628d54) - targetting and add shape to ndarray *(PR [#891](https://github.com/dbbs-lab/bsb-core/pull/891) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#869](https://github.com/dbbs-lab/bsb-core/issues/869) opened by [@drodarie](https://github.com/drodarie)*
  - :arrow_lower_right: *fixes issue [#890](https://github.com/dbbs-lab/bsb-core/issues/890) opened by [@drodarie](https://github.com/drodarie)*


## [v4.5.1] - 2024-10-12
### :bug: Bug Fixes
- [`ab77c6f`](https://github.com/dbbs-lab/bsb-core/commit/ab77c6fbe14ed298c770e68fe31a64ccd6588d0c) - count_ratio on non overlapping partitions *(PR [#886](https://github.com/dbbs-lab/bsb-core/pull/886) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#885](https://github.com/dbbs-lab/bsb-core/issues/885) opened by [@drodarie](https://github.com/drodarie)*
  - :arrow_lower_right: *fixes issue [#889](https://github.com/dbbs-lab/bsb-core/issues/889) opened by [@drodarie](https://github.com/drodarie)*


## [v4.5.0] - 2024-09-13
### :sparkles: New Features
- [`9f4046a`](https://github.com/dbbs-lab/bsb-core/commit/9f4046a2b40ad40257bf7ab13297d4441d43d02f) - Stack regions and Layer partitions *(PR [#868](https://github.com/dbbs-lab/bsb-core/pull/868) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *addresses issue [#867](https://github.com/dbbs-lab/bsb-core/issues/867) opened by [@marialauradeg98](https://github.com/marialauradeg98)*


## [v4.4.4] - 2024-09-13
### :bug: Bug Fixes
- [`43ef230`](https://github.com/dbbs-lab/bsb-core/commit/43ef2308e6f742f195830adddc3934d2cee59561) - update morphology introduce_point function *(PR [#884](https://github.com/dbbs-lab/bsb-core/pull/884) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#883](https://github.com/dbbs-lab/bsb-core/issues/883) opened by [@drodarie](https://github.com/drodarie)*


## [v4.4.3] - 2024-09-02
### :bug: Bug Fixes
- [`903434b`](https://github.com/dbbs-lab/bsb-core/commit/903434b3c4a7b7acdb78b3f1e2dee93aea5c3062) - group chunks for placement from different partitions to avoid duplicates *(PR [#880](https://github.com/dbbs-lab/bsb-core/pull/880) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#879](https://github.com/dbbs-lab/bsb-core/issues/879) opened by [@francesshei](https://github.com/francesshei)*


## [v4.4.2] - 2024-08-02
### :bug: Bug Fixes
- [`97978b4`](https://github.com/dbbs-lab/bsb-core/commit/97978b433dba579478387760010dfd7b09bfda19) - use OIDC instead of user token to publish to pypi *(PR [#877](https://github.com/dbbs-lab/bsb-core/pull/877) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#876](https://github.com/dbbs-lab/bsb-core/issues/876) opened by [@drodarie](https://github.com/drodarie)*


## [v4.4.1] - 2024-08-02
### :bug: Bug Fixes
- [`e4c194c`](https://github.com/dbbs-lab/bsb-core/commit/e4c194ce9c7b4f3bc41f7589954a98d204e8d9fb) - make gha checks (docs, build, etc) triggered by main workflows *(PR [#874](https://github.com/dbbs-lab/bsb-core/pull/874) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#873](https://github.com/dbbs-lab/bsb-core/issues/873) opened by [@drodarie](https://github.com/drodarie)*
- [`09ab71f`](https://github.com/dbbs-lab/bsb-core/commit/09ab71fb4d3301a69e51395d16d1e26d50c23591) - change bump refs to tag-release *(PR [#875](https://github.com/dbbs-lab/bsb-core/pull/875) by [@drodarie](https://github.com/drodarie))*


## 4.4.0
### :sparkles: New Features
- [`f234265`](https://github.com/dbbs-lab/bsb-core/commit/f234265cbab4cd370332eb7dea794f872f6728d8) - add conventional commits and auto release *(PR #864 by @drodarie)*
  - :arrow_lower_right: *addresses issue #860 opened by @Helveg*

### :bug: Bug Fixes
- [`32799b4`](https://github.com/dbbs-lab/bsb-core/commit/32799b4961811ac977dffafb49f3465ae9d6ab15) - use github app to bypass the main branch protections. *(PR #872 by @drodarie)*
  - :arrow_lower_right: *fixes issue #870 opened by @drodarie*

## 4.3.0
* Introduction of a pool caching system
* Fix run iteration values in core
* Add FixedOutdegree

## 4.2.0
* Created geometric shape connection strategies
* Added support for multiple shapes for each cell type
* Written docs for geometric shapes
* fix typing and casting of post connectivity hooks
* fix readthedocs conflicts with furo package
* Add test to check if Allen API is down and skip related tests

## 4.1.1
* Fix reference of file_ref during configuration parsing when importing nodes.
* Use a more strict rule for Jobs enqueuing.
* Use certifi to fix ssl certificate issues.

## 4.1.0
* Added `ParsesReferences` mixin from bsb-json to allow reference and import in configuration files.
  This includes also a recursive parsing of the configuration files.
* Added `swap_axes` function in morphologies
* Added API test in pre-commit config and fix duplicate entries.
* Fix `PackageRequirement`, `ConfigurationListAttribute`, and `ConfigurationDictAttribute`
  inverse functions
* Refactor `CodeDependencyNode` module attribute to be either a module like string or a path string
* Fix of assert_same_len
* Fix of test_particle_vd

# 4.0.0 - Too much to list

## 40.0.0a32

### Breaking changes

* Bumped to `bsb-hdf5~=0.3.1`, to fix #579.
* Renamed `MPI.*` functions to lowercase.

## 40.0.0a30

* BSB now requires bsb-hdf5 v 0.2.5

## 4.0.0a19

* Removed the `voxels` property of the `Voxels` partition, instead the children ``nrrd``
  and ``allen`` are now available directly as partitions.
* Renamed the `AllenStructureLoader` to `AllenStructure`

## 4.0.0a18

### Breaking changes

* Renamed `cls` of placement and connectivity strategies to `strategy`.
* Renamed `cls` of region to `type`.

### Features

* Added layouts (#492).

## 4.0.0a9 - 4.0.0a17

* Added `RandomPlacement` strategy.
* Added autolink for config, use it by default.
* Fixed BSB under Jupyter notebook conditions.
* `AllenStructureLoader` has a defined public API now, of classmethods, to lookup structs.

## 4.0.0a8

* Improved storage interface documentation.
* Fixed local modules not being found by config (#386).
* Fixed inheritance and signatures of `TouchDetector`.
* Documented cell types (#424).
* Fixed dynamic node initialization (#425).
* Fixed config dictionary copying (#432).
* Added `MorphologySet.empty` (#426).
* Fixed morphology property loading from MR (#434).
* Fixed dissapearance of warnings when config loading errors out (#440).
* Allow wildcards in `by_name` morphology selector.
* Added copy button to documentation code blocks (#446).
* Warn and skip connections when no cells are placed (#442).
* Fixed 2d indexing of VoxelData class (#437).
* Load meta dictionary of morphologies (#435).
* Fixed error with queued jobs when dependency isn't queued (#445).

## 4.0.0a7

### Breaking changes

* `morphological` changed to `morphologies`.
* `geometrical` changed to `geometry`.

# 3.10 - Arbor

* Added a very basic Arbor adapter

# 3.9

## 3.9.0 - Partial (re)connecting, network merging and repeated NEST simulations

* WARNING: Removed the cell cache API, the cell cache is still there internally but
  spoofed and not to be used relied on in any user code anymore!
* Running repeated NEST simulations no longer causes strange IO issues, growing
  device labels, or module loading warnings and has an example (#280, #292, #295).
* Added support for partial (re)connection of networks (#303).
* The PlacementSet API can now be used during labelled connectivity by passing the
  `labels` kwarg. The labels of the current connection can be accessed inside the
  `connect` function as `self.label_pre` and `self.label_post` (#310).
* Added `network.merge` function (#278).
* Added `get_rank` and `broadcast` to adapter interface so that `mpi4py` can
  remain an optional dependency (#283).
* More progress reporting during reconstruction (#305).
* Fixed NEST spike recorders (#284).
* Added NEST fork installation instructions.
* Added support for external sources of placement and connectivity (#273).

# 3.8

## 3.8.0 - Added a bit of love for the NEURON adapter

* BREAKING: NEURON devices will by default target all sections instead of 1
  soma section.
* BREAKING: `section_type` changed to `section_types` list for devices.
* BREAKING: All `NeuronDevice` child implementations need to override
  `validate_specifics` where each can validate their config.
* BREAKING: Fixed the long standing bug that spikes in NEURON where recorded
  as (2xN) instead of (Nx2) datasets.
* BREAKING: `adapter.collect_output` must be passed the `simulation` object.
* Fixed a bug where `spike_devices` with fixed spike times didn't record data.
* NEURON adapter now uses `nrn-patch` v3.0.0
* Added a `voltage_clamp` NEURON device.
* Added support for weight recorders in the NEST adapter (#248).
* NEST adapter's `spike_recorder` stores all cell types that occur in a dataset,
  is used later on to infer display information when plotting.
* NEURON adapter's `LocationRecorder` now stores section id.
* Network-cache phased out of targetting mechanisms.
* Added `__main__.py` for situations where shell command is unavailable.
* Added `network.get_gid_types` to retrieve the cell types of a vector of GIDs.
* Added `network.assert_continuity` to check all `PlacementSet`s form a single
  continuous chain of GIDs starting from 0.
* Fixed a bug where relays without targets would cause errors.
* Fixed NEURON adapter's `time` vector in result files.
* Fixed NEURON adapter's `index_relays` for targetless relays.
* Added stricter validation of config for the `SpikeGenerator` device.
* [cerebellum] Optimized Golgi to granule cell connectivity algorithm.
* [cerebellum] Optimized mossy to glomerulus connectivity algorithm.
* Added `branch.children`.
* Added `cell_type.get_placement_set`.
* Added `get_result_config`.
* Added a `--version` command to the CLI.
* The `time` recorder for NEURON simulations is fixed.
* `*.h5` files and the `build` directory are gitignored.
* Added `range` kwarg to `plot_traces`.
* `plot_traces` will pass all extra kwargs to the `make_subplots` call.
* Added `gaps` kwarg to `hdf5_plot_psth` to control gaps in Bar graph.
* Plot axis labels now display units in square brackets.
* Added an example that shows how to color the branches of a morphology by type.

# 3.7

## 3.7.7

* Fixed broken on release `by_label` targetting
* `mouse_cerebellum_cortex.json` is now scalable and ID-free.

## 3.7.6

* Added `by_label` targetting mechanism
* Changed `mouse_cerebellum_cortex.json` to avoid the use of concrete IDs

## 3.7.5

* Cell IDs persistently increment across Python sessions.
* Added CONTRIBUTING & CODE_OF_CONDUCT
* NEST devices can be configured without targets, for manual targetting.
* NEST master seed is determined by clocktime but can be fixed.
* Added `bsb.core.Scaffold.get_connectivity_sets`


## 3.7.4

* Added raw config string to result files for reference.

## 3.7.3

* Bumped minimum nrn-patch to 3.0.0b3 to fix transfer variable stalling.

## 3.7.2

* Advertise compatible Python versions in `setup.py`
* Bumped minimum numpy to 1.19.0
* Bumped minimum nrn-patch to 3.0.0b1

## 3.7.1

* Fixed a bug with nest and MPI. (see #230)

## 3.7.0

* The NEURON adapter now supports source variables.
* Gap junctions were added to the model of the cerebellum.

# 3.6

## 3.6.7

* Altered NMDA channels.

## 3.6.6

* The return values of simulations are now the path to their result file.

## 3.6.5

* Fixed a bug with the NEURON adapter transmitter map causing loss of spike transmission.

## 3.6.4

* Slightly changed the `neuron` install workflow. NEURON is now pip installed

## 3.6.3

* Updated "Getting Started" guide.
* Changed default config to `network_configuration.json`

## 3.6.2

* New ionic recorder device for NEURON adapter.

## 3.6.0b1

* Added GC-GC, SC-SC & BC-BC GABA connections

## 3.6.0b0

* Morphology rework: they are now branch centric structures of arrays.
  * Backward compatible `compartments` system still available.

# 3.5.0

* Blender support

# 3.3.0

* FiberIntersection added.

# 3.2

## 3.2.13

* First version with a functional multicompartmental network.

## 3.2.1

* PlacementSets have been introduced (#303)
* Obfuscated setup uses scaffold version plus "rc0". (#301, #308)
* `placement.py` is now its own module. (#302)
* ConfigurableClasses can specify classes in the global namespace instead of only inside
  of modules. (#299)

## 3.2.0

* Added parallel neuron simulations

# 3.0

## 3.0.4

* Cilindrical targetting mechanism for devices.
* Fixed `scaffold simulate`

## 3.0.3

* Added changes for the hackathon.
* Fixed bugs that would have been encountered during the workshop.

## 3.0.2

* Added obfuscation scripts to create distributions that are obfuscated and
  expire after a certain date.

## 3.0.1

* Fixed particle placement for layers that don't originate in the coordinate
  system origin. (PR #150)
* Better NEST warnings/errors for module errors.
* CLI commands `compile` and `run` can resize the configuration with -x and -z.
* Switched to Travis CI
* Optimized AllToAll connectivity strategy.
* Sattelite placement strategy now respects simulation volume bounds.
* Addition of mossy fiber to glomerulus connectivity. (PR #167)
* Fixed some of the issues with ParticlePlacement.

## 3.0.0

* Multi-instancing

## Alpha version 6
* Particle placement for IO
* EvalConfigurations

## Alpha version 5
* Merged in the plasticity branch
* IO placement & connectivity
* DCN interneurons

## Alpha version 4

## Minor changes

* Fixed to a runnable state.

## Alpha version 3

### Major changes
* Merged touch detection branch
  * 3D touch detection, can be reduced to 2 or 1 dimension cell intersection.
  * Select from & to cell type & compartment type.
  * Ability to auto-discover cell search radius or to specify it yourself.
    Compartment needs to be specified (default 5µm)
  * Configure amount of synapses with a constant or distribution

## Alpha version 2

### Major changes

* Cross-platform pip entry-points (console scripts such as `scaffold compile`)
* Merged in the plasticity branch
  * Setting `"plastic": true` in a NestConnection configuration will set it up
    as a plastic connection with volume transmitters attached
  * Specifying to which receptor type a plastic connection is connected can be
    done by providing a dictionary mapping the partner cell type to a receptor
    type id in the configuration of cell types under `receptors`
* Removed dependency on archaic `matplotlib` and added `plotly`. Plotting
  dependencies are optionally installed using `pip install
  dbbs-scaffold[with-plotting]`
* NEST modules to load can be specified in the configuration.
* scipy.stats.distributions classes can be configured using
  `DistributionConfiguration`s.
* Datasets in the `/cells/connections` group of an output HDF5 file can store
  metadata on them
  * The metadata keys `from_cell_types` and `to_cell_types` can help clarify
    which cell_types are actually contained within the dataset when the
    ConnectionStrategy has multiple types.
* Added a overloadable `boot` method to ConfigurableClass that is executed after
  `__init__` and before `validate`

### Minor changes

* NEST simulator resolution can be set
* Cells can be placed by an absolute amount instead of just densities.
  * For very low amounts of cells to be placed there is a minimum of 1 per
    sublayer.
* Renamed `addCellType` to `add_cell_type` in `configuration.py`.
* Added a `report` function to `scaffold.py` for verbosity compliant prints.
* IllegalConnection errors by NEST are now caught to display the device that
  causes them.

### Tests

* Added single and double cell type creation tests for NEST adapter.

# 2.3
This release is a prerelease of version 3.0 with finished simulator handling for
the NEST simulator and preliminary support for TreeCollections, tree pickling,
MorphologyRepositories, morphologies, voxelization and touch detection.

* Added MorphologyRepositories to preprocess and store morphologies before they
  are used in the placement/connectivity.
* Added TreeCollections to load, cache and store trees. OutputFormatters should
  know how to handle trees.
* HDF5Formatter can pickle trees.
* Simulations can be configured through SimulatorAdapters, should provide
  ConfigurableClasses to configure `cell_models`, `connection_models` and
  `devices`.
* Implemented a NestAdapter with NestCells, NestConnections and NestDevices.

# 2.2

## 2.2.2
* Changed dependency list for installs outside of Anaconda.

## 2.2.1
* Removed obsolete files transferred by bad merge.

## 2.2.0
* Released 2.1.3 as 2.2.0

# 2.1

## 2.1.3
* Removed dependency on pandas
* Added a list of dependencies to setup.py

## 2.1.2
* Reworked/fixed connectivity algorithm between Golgi and granule cells.

## 2.1.1
* CHANGELOG restructured to show newest first.
* Removed dependency on pint and quantulum3.

## 2.1.0
* README updated.
* Verbosity added.
* Command line interface added. (Linux version not tested)

# 2.0

## 2.0.1
* README updated.

## 2.0.0
* Complete rework of the codebase to ensure flexibility, scalability and
  adoption by the community.
* First steps of distribution as a Python package.
[v4.4.1]: https://github.com/dbbs-lab/bsb-core/compare/v4.4.0...v4.4.1
[v4.4.2]: https://github.com/dbbs-lab/bsb-core/compare/v4.4.1...v4.4.2
[v4.4.3]: https://github.com/dbbs-lab/bsb-core/compare/v4.4.2...v4.4.3
[v4.4.4]: https://github.com/dbbs-lab/bsb-core/compare/v4.4.3...v4.4.4
[v4.5.0]: https://github.com/dbbs-lab/bsb-core/compare/v4.4.4...v4.5.0
[v4.5.1]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.0...v4.5.1
[v4.5.2]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.1...v4.5.2
[v4.5.3]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.2...v4.5.3
[v4.5.4]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.3...v4.5.4
[v4.5.5]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.4...v4.5.5
[v5.0.0]: https://github.com/dbbs-lab/bsb-core/compare/v4.5.5...v5.0.0
[v5.0.1]: https://github.com/dbbs-lab/bsb-core/compare/v5.0.0...v5.0.1
[v5.0.2]: https://github.com/dbbs-lab/bsb-core/compare/v5.0.1...v5.0.2
[v5.1.0]: https://github.com/dbbs-lab/bsb-core/compare/v5.0.2...v5.1.0
[v5.1.1]: https://github.com/dbbs-lab/bsb-core/compare/v5.1.0...v5.1.1
