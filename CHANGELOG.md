# 8.0.0 (2026-10-15)

### 🚀 Features

- numpy 2.x compatibility ([#240](https://github.com/dbbs-lab/bsb/pull/240))
- Add distribution based placement ([#242](https://github.com/dbbs-lab/bsb/pull/242))
- Rust acceleration for segment intersection touch detection and Poisson-disk placement ([#256](https://github.com/dbbs-lab/bsb/pull/256))
- **bsb-core:** add an after_simulation hook ([#257](https://github.com/dbbs-lab/bsb/pull/257))
- ⚠️  **bsb-core:** give the prepared simulation a hook of its own ([#263](https://github.com/dbbs-lab/bsb/pull/263))
- ⚠️  **bsb-core:** drop the adapter's post_prepare argument ([#278](https://github.com/dbbs-lab/bsb/pull/278))
- ⚠️  **bsb-core:** parameters answer what a model's values are, per arity ([#260](https://github.com/dbbs-lab/bsb/pull/260))
- **bsb-core:** configured randomness, with replicates and reproduction ([#264](https://github.com/dbbs-lab/bsb/pull/264))
- ⚠️  **bsb-core:** draw placement from the configured randomness ([#276](https://github.com/dbbs-lab/bsb/pull/276))
- ⚠️  **bsb-core:** draw connectivity from the configured randomness ([#277](https://github.com/dbbs-lab/bsb/pull/277))
- ⚠️  **bsb-core:** a run ends with one results file, whatever it took to make it ([#266](https://github.com/dbbs-lab/bsb/pull/266))
- ⚠️  **bsb-core:** record one signal per cell, annotated the same way everywhere ([#272](https://github.com/dbbs-lab/bsb/pull/272))
- ⚠️  **bsb-core:** a device records every cell it watched ([#290](https://github.com/dbbs-lab/bsb/pull/290))
- ⚠️  **bsb-core:** recordings say what they recorded, and read_results traces it back to the network ([#293](https://github.com/dbbs-lab/bsb/pull/293), [#288](https://github.com/dbbs-lab/bsb/issues/288))
- ⚠️  **bsb-nest:** seed the kernel from the network's randomness ([#275](https://github.com/dbbs-lab/bsb/pull/275))

### 🩹 Fixes

- ⚠️  Let writing data to file at flush ([#213](https://github.com/dbbs-lab/bsb/pull/213))
- Python 3.13 and 3.14 compatibility, arbor 0.12 ([#249](https://github.com/dbbs-lab/bsb/pull/249))
- code dependency config for dotted paths. ([#255](https://github.com/dbbs-lab/bsb/pull/255))
- ⚠️  seed postprocessing hooks and Distribution draws; require Python 3.11 ([#291](https://github.com/dbbs-lab/bsb/pull/291))
- ⚠️  **bsb-arbor:** draw the poisson generators from the network's randomness ([#280](https://github.com/dbbs-lab/bsb/pull/280))
- **bsb-core:** parse config package requirements into a slotted subclass ([#268](https://github.com/dbbs-lab/bsb/pull/268))
- **bsb-core:** attribute configuration errors to the node they happened on ([#273](https://github.com/dbbs-lab/bsb/pull/273), [#67](https://github.com/dbbs-lab/bsb/issues/67), [#45](https://github.com/dbbs-lab/bsb/issues/45), [#59](https://github.com/dbbs-lab/bsb/issues/59))
- **bsb-core:** stop re-parsing pyproject.toml per report, and survive an offline fetch ([#269](https://github.com/dbbs-lab/bsb/pull/269))
- ⚠️  **bsb-core:** store structured metadata so it survives being written ([#262](https://github.com/dbbs-lab/bsb/pull/262))
- ⚠️  **bsb-core:** draw device targets the same way on every rank ([#265](https://github.com/dbbs-lab/bsb/pull/265))
- ⚠️  **bsb-core:** the soma is every location labelled soma ([#295](https://github.com/dbbs-lab/bsb/pull/295))
- ⚠️  **bsb-core:** multiplex per-device recordings instead of one Neo object per cell ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- **bsb-hdf5:** count placement sets from the tracked chunk stats ([#270](https://github.com/dbbs-lab/bsb/pull/270), [#26](https://github.com/dbbs-lab/bsb/issues/26), [#28](https://github.com/dbbs-lab/bsb/issues/28))
- **bsb-nest:** install NEST without a synced environment ([#279](https://github.com/dbbs-lab/bsb/pull/279))
- ⚠️  **bsb-neuron:** default synapse delay to 1 ms, and drop the unrunnable Convergence strategy ([#271](https://github.com/dbbs-lab/bsb/pull/271), [#99](https://github.com/dbbs-lab/bsb/issues/99), [#136](https://github.com/dbbs-lab/bsb/issues/136))
- **release:** bump sibling pins on release and stop skipping the release run ([#259](https://github.com/dbbs-lab/bsb/pull/259), [#193](https://github.com/dbbs-lab/bsb/issues/193))

### ⚠️  Breaking Changes

- **bsb-core:** multiplex per-device recordings instead of one Neo object per cell  ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- seed postprocessing hooks and Distribution draws; require Python 3.11  ([#291](https://github.com/dbbs-lab/bsb/pull/291))
  BSB requires Python 3.11 or newer. Every package's
  `requires-python` moves from `>=3.10,<4` to `>=3.11,<4`.
- **bsb-core:** the soma is every location labelled soma  ([#295](https://github.com/dbbs-lab/bsb/pull/295))
  `SomaTargetting` targets the locations labelled `soma` instead of
  location (0, 0). A cell whose morphology labels no soma has no soma locations, so
  devices that default to it (voltage recorder, current and voltage clamp, spike
  generator) target nothing on such a cell.
- **bsb-core:** recordings say what they recorded, and read_results traces it back to the network  ([#293](https://github.com/dbbs-lab/bsb/pull/293), [#288](https://github.com/dbbs-lab/bsb/issues/288))
  the `cell_type` annotation of recordings and
  `Recording.cell_type` are renamed to `cell_model`. On NEST and arbor,
  `cell_id` is the cell's placement set id instead of the simulator's node id
  or gid.
- **bsb-core:** a device records every cell it watched  ([#290](https://github.com/dbbs-lab/bsb/pull/290))
  recordings no longer carry `gids` or `pop_size`. A device's
  recordings are the cells it watched, so their number is the population and their
  `cell_id`s are which cells.
  Claude-Session: https://claude.ai/code/session_017Zcwom5VRiA5WMreKncmVg
- **bsb-core:** record one signal per cell, annotated the same way everywhere  ([#272](https://github.com/dbbs-lab/bsb/pull/272))
- **bsb-core:** a run ends with one results file, whatever it took to make it  ([#266](https://github.com/dbbs-lab/bsb/pull/266))
  `bsb simulate` writes one file per run rather than one per rank,
  and `SimulationResult` gains `finalize`, which an adapter driving the result
  itself has to call.
  Claude-Session: https://claude.ai/code/session_01BHScuq1Hoemb5AUeofueWP
- **bsb-nest:** seed the kernel from the network's randomness  ([#275](https://github.com/dbbs-lab/bsb/pull/275))
  `seed` is no longer configured on a NEST simulation. Pin the
  network's `rng.seed`, or declare an `rng.settings` entry of strategy `nest` and
  name it on the simulation's `rng`.
  Claude-Session: https://claude.ai/code/session_017Zcwom5VRiA5WMreKncmVg
- **bsb-core:** draw connectivity from the configured randomness  ([#277](https://github.com/dbbs-lab/bsb/pull/277))
- **bsb-core:** draw placement from the configured randomness  ([#276](https://github.com/dbbs-lab/bsb/pull/276))
- **bsb-arbor:** draw the poisson generators from the network's randomness  ([#280](https://github.com/dbbs-lab/bsb/pull/280))
- **bsb-core:** draw device targets the same way on every rank  ([#265](https://github.com/dbbs-lab/bsb/pull/265))
  a device targetting a `fraction` or `count` of a population
  selects a different subset than before, since the selection is now seeded.
- **bsb-core:** parameters answer what a model's values are, per arity  ([#260](https://github.com/dbbs-lab/bsb/pull/260))
  `Parameter` no longer has a `value` attribute and
  `ParameterValue` is removed. `CellModel.parameters` is a dict keyed by the model
  parameter, not a list. `constants` blocks no longer accept a computed parameter;
  write it in `parameters`. `resolution` is configured on any simulation, not only
  per backend.
- **bsb-core:** store structured metadata so it survives being written  ([#262](https://github.com/dbbs-lab/bsb/pull/262))
  the `config` annotation on a result block is a JSON string rather
  than a dict, in memory as well as on file. Keeping it a dict in memory and a
  string on file would reintroduce exactly the trap that caused this. Read it with
  `read_simulation_config`.
- **bsb-core:** drop the adapter's post_prepare argument  ([#278](https://github.com/dbbs-lab/bsb/pull/278))
- **bsb-core:** give the prepared simulation a hook of its own  ([#263](https://github.com/dbbs-lab/bsb/pull/263))
  `post_prepare` on a simulation is replaced by `after_prepare`,
  whose entries are named dynamic nodes with a `strategy` rather than a list of
  dotted function paths.
  Claude-Session: https://claude.ai/code/session_01BHScuq1Hoemb5AUeofueWP
- **bsb-neuron:** default synapse delay to 1 ms, and drop the unrunnable Convergence strategy  ([#271](https://github.com/dbbs-lab/bsb/pull/271), [#99](https://github.com/dbbs-lab/bsb/issues/99), [#136](https://github.com/dbbs-lab/bsb/issues/136))
  `bsb.connectivity.Convergence` and the `bsb.Convergence`
  public API entry are removed. Configurations using
  `strategy: bsb.connectivity.Convergence` did not work; use
  `bsb.connectivity.FixedIndegree` or a custom strategy instead.
  Closes #99
- Let writing data to file at flush  ([#213](https://github.com/dbbs-lab/bsb/pull/213))

### ❤️ Thank You

- Claude Opus 4.6
- Claude Opus 4.8 (1M context)
- Claude Opus 5
- Claude Opus 5 (1M context)
- Claude Sonnet 4.6
- Claude Sonnet 5
- Dimitri Rodarie
- Dimitri RODARIE
- Filippo @filimarc
- Robin De Schepper

## 7.6.1 (2026-09-18)

### 🩹 Fixes

- **bsb-nest:** version-guarded NESTErrors import for NEST 3.10 compatibility | add packaging 26.2+ compatibility ([#287](https://github.com/dbbs-lab/bsb/pull/287))

### ❤️ Thank You

- Filippo @filimarc

## 7.6.0 (2026-06-30)

### 🚀 Features

- **bsb-hdf5:** batched HDF5 handle scopes, job-pool dependency fixes, and connect-job tracing ([#250](https://github.com/dbbs-lab/bsb/pull/250), [#223](https://github.com/dbbs-lab/bsb/issues/223), [#1](https://github.com/dbbs-lab/bsb/issues/1))

### ❤️ Thank You

- Robin De Schepper

## 7.5.1 (2026-06-30)

### 🩹 Fixes

- **bsb-nest:** isolate the validation kernel per simulation ([#251](https://github.com/dbbs-lab/bsb/pull/251))

### ❤️ Thank You

- Robin De Schepper

## 7.5.0 (2026-06-30)

### 🚀 Features

- **config:** out-of-process NEST kernel for config-build-time checks ([#227](https://github.com/dbbs-lab/bsb/pull/227), [#235](https://github.com/dbbs-lab/bsb/pull/235), [#228](https://github.com/dbbs-lab/bsb/issues/228))

### ❤️ Thank You

- Robin De Schepper

## 7.4.0 (2026-05-29)

### 🚀 Features

- Mature OpenTelemetry integration ([#223](https://github.com/dbbs-lab/bsb/pull/223), [#1](https://github.com/dbbs-lab/bsb/issues/1))

### ❤️ Thank You

- Robin De Schepper

## 7.3.1 (2026-04-16)

### 🩹 Fixes

- Loading modules to check NEST models ([#228](https://github.com/dbbs-lab/bsb/pull/228))
- Nest installation with Nx ([4bd2458](https://github.com/dbbs-lab/bsb/commit/4bd2458))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

## 7.3.0 (2026-03-20)

### 🚀 Features

- overwrite labels for ps ([#224](https://github.com/dbbs-lab/bsb/pull/224))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.3 (2026-02-21)

### 🩹 Fixes

- rectified proxy location accessor behavior ([#219](https://github.com/dbbs-lab/bsb/pull/219))

### ❤️ Thank You

- Robin De Schepper

## 7.2.2 (2026-02-21)

### 🩹 Fixes

- bump mpi4py and minor fixes ([#221](https://github.com/dbbs-lab/bsb/pull/221))
- bump mpi4py for libs ([0951e81](https://github.com/dbbs-lab/bsb/commit/0951e81))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

## 7.2.1 (2026-01-19)

### 🩹 Fixes

- Replace MPI barrier with an error collection system ([#212](https://github.com/dbbs-lab/bsb/pull/212))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.0 (2026-01-13)

### 🚀 Features

- Added support for MorphIO options and fixed single point branches in NEURON builder ([#210](https://github.com/dbbs-lab/bsb/pull/210))

### ❤️ Thank You

- Robin De Schepper

## 7.1.0 (2026-01-09)

### 🚀 Features

- Add Class to fuse connections ([#203](https://github.com/dbbs-lab/bsb/pull/203))

### ❤️ Thank You

- Filippo @filimarc

## 7.0.3 (2025-12-17)

### 🩹 Fixes

- CLI simulate and ExtNestDevice ([#207](https://github.com/dbbs-lab/bsb/pull/207), [#204](https://github.com/dbbs-lab/bsb/issues/204), [#206](https://github.com/dbbs-lab/bsb/issues/206))

### ❤️ Thank You

- Dimitri RODARIE

## 7.0.2 (2025-12-12)

### 🩹 Fixes

- Caching morphology loaders during placement ([#208](https://github.com/dbbs-lab/bsb/pull/208))

### ❤️ Thank You

- Dimitri RODARIE

## 7.0.1 (2025-11-18)

### 🩹 Fixes

- bump bsb versions in toml ([#195](https://github.com/dbbs-lab/bsb/pull/195), [#197](https://github.com/dbbs-lab/bsb/issues/197), [#187](https://github.com/dbbs-lab/bsb/issues/187))

### ❤️ Thank You

- Dimitri RODARIE

# 7.0.0 (2025-11-17)

### 🚀 Features

- ⚠️  Refactor Voxel partitions - Simulation controllers ([#191](https://github.com/dbbs-lab/bsb/pull/191), [#148](https://github.com/dbbs-lab/bsb/issues/148), [#145](https://github.com/dbbs-lab/bsb/issues/145), [#146](https://github.com/dbbs-lab/bsb/issues/146), [#177](https://github.com/dbbs-lab/bsb/issues/177), [#169](https://github.com/dbbs-lab/bsb/issues/169), [#181](https://github.com/dbbs-lab/bsb/issues/181), [#184](https://github.com/dbbs-lab/bsb/issues/184), [#171](https://github.com/dbbs-lab/bsb/issues/171), [#182](https://github.com/dbbs-lab/bsb/issues/182), [#186](https://github.com/dbbs-lab/bsb/issues/186), [#174](https://github.com/dbbs-lab/bsb/issues/174), [#44](https://github.com/dbbs-lab/bsb/issues/44), [#175](https://github.com/dbbs-lab/bsb/issues/175), [#149](https://github.com/dbbs-lab/bsb/issues/149), [#189](https://github.com/dbbs-lab/bsb/issues/189))

### ⚠️  Breaking Changes

- ⚠️  Refactor Voxel partitions - Simulation controllers ([#191](https://github.com/dbbs-lab/bsb/pull/191), [#148](https://github.com/dbbs-lab/bsb/issues/148), [#145](https://github.com/dbbs-lab/bsb/issues/145), [#146](https://github.com/dbbs-lab/bsb/issues/146), [#177](https://github.com/dbbs-lab/bsb/issues/177), [#169](https://github.com/dbbs-lab/bsb/issues/169), [#181](https://github.com/dbbs-lab/bsb/issues/181), [#184](https://github.com/dbbs-lab/bsb/issues/184), [#171](https://github.com/dbbs-lab/bsb/issues/171), [#182](https://github.com/dbbs-lab/bsb/issues/182), [#186](https://github.com/dbbs-lab/bsb/issues/186), [#174](https://github.com/dbbs-lab/bsb/issues/174), [#44](https://github.com/dbbs-lab/bsb/issues/44), [#175](https://github.com/dbbs-lab/bsb/issues/175), [#149](https://github.com/dbbs-lab/bsb/issues/149), [#189](https://github.com/dbbs-lab/bsb/issues/189))

### ❤️ Thank You

- Dimitri RODARIE

## 6.0.7 (2025-10-06)

### 🩹 Fixes

- `insert_transmitter` unique under NEURON 9 ([#177](https://github.com/dbbs-lab/bsb/pull/177))
- click default value test for None values ([077e582](https://github.com/dbbs-lab/bsb/commit/077e582))

### ❤️ Thank You

- drodarie
- Robin De Schepper

## 6.0.6 (2025-08-26)

### 🩹 Fixes

- warn when hdf5 lock slower than mpilock ([#166](https://github.com/dbbs-lab/bsb/pull/166))

### ❤️ Thank You

- Robin De Schepper

## 6.0.5 (2025-08-26)

### 🩹 Fixes

- bump nightly ([#165](https://github.com/dbbs-lab/bsb/pull/165))

### ❤️ Thank You

- Robin De Schepper

## 6.0.4 (2025-07-31)

### 🩹 Fixes

- applied a fix for targeting strategies ([#164](https://github.com/dbbs-lab/bsb/pull/164))

### ❤️ Thank You

- Filippo @filimarc

## 6.0.3 (2025-07-25)

### 🩹 Fixes

- Adapt NeuronPopulation getitem to check for NumPy types ([#161](https://github.com/dbbs-lab/bsb/pull/161))

### ❤️ Thank You

- Filippo @filimarc

## 6.0.2 (2025-07-18)

### 🩹 Fixes

- nx commands ([#153](https://github.com/dbbs-lab/bsb/pull/153))

### ❤️ Thank You

- Dimitri RODARIE

## 6.0.1 (2025-07-16)

### 🩹 Fixes

- patch documentation and gha ([#147](https://github.com/dbbs-lab/bsb/pull/147), [#144](https://github.com/dbbs-lab/bsb/issues/144), [#142](https://github.com/dbbs-lab/bsb/issues/142))
- release GHA, install mpi deps ([f206164](https://github.com/dbbs-lab/bsb/commit/f206164))
- update_codemeta.py to adapt to new location ([2f4f552](https://github.com/dbbs-lab/bsb/commit/2f4f552))
- retrieve new version from update_codemeta.py for release GHA ([d8018e3](https://github.com/dbbs-lab/bsb/commit/d8018e3))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

# 6.0.0 (2025-06-11)

This was a version bump only, there were no code changes.

# 5.0.0 (2025-06-11)

### 🚀 Features

- ⚠️  Integrated BSB landscape into a monorepository ([#143](https://github.com/dbbs-lab/bsb/pull/143), [#6](https://github.com/dbbs-lab/bsb/issues/6), [#3458](https://github.com/dbbs-lab/bsb/issues/3458))

### ⚠️  Breaking Changes

- ⚠️  Integrated BSB landscape into a monorepository ([#143](https://github.com/dbbs-lab/bsb/pull/143), [#6](https://github.com/dbbs-lab/bsb/issues/6), [#3458](https://github.com/dbbs-lab/bsb/issues/3458))

### ❤️ Thank You

- Robin De Schepper

## 6.0.0-a4 (2025-06-10)

### 🚀 Features

- ⚠️  add boolean flag when initializing Scaffold to force update the configuration ([#6](https://github.com/dbbs-lab/bsb/issues/6))
- add send coverage script to GHA ([c620e6a](https://github.com/dbbs-lab/bsb/commit/c620e6a))
- add pull request GHA ([7d100a2](https://github.com/dbbs-lab/bsb/commit/7d100a2))
- add GHA for external PRs ([f371423](https://github.com/dbbs-lab/bsb/commit/f371423))
- add hook for bsb-core api ([ca337d6](https://github.com/dbbs-lab/bsb/commit/ca337d6))

### 🩹 Fixes

- bsb-neuron lint and tests ([9118dca](https://github.com/dbbs-lab/bsb/commit/9118dca))
- packages version in __init__.py with respect to .toml ([52f6672](https://github.com/dbbs-lab/bsb/commit/52f6672))
- nrn-patch tests and glia coverage ([630b1ec](https://github.com/dbbs-lab/bsb/commit/630b1ec))
- lint pass on nrn-patch and bsb-neuron ([7385a32](https://github.com/dbbs-lab/bsb/commit/7385a32))
- lint on bsb-core and format every package ([0725784](https://github.com/dbbs-lab/bsb/commit/0725784))
- move bsb-core codecov config and readmes to the main folder. ([f8ef62b](https://github.com/dbbs-lab/bsb/commit/f8ef62b))
- neuron 8.2.7 still does not include nmodl, falling back to neuron-nightly ([7e13be0](https://github.com/dbbs-lab/bsb/commit/7e13be0))
- nest tests and nrn-patch docs ([d58976e](https://github.com/dbbs-lab/bsb/commit/d58976e))
- GHA for RTD docs preview ([d95c14d](https://github.com/dbbs-lab/bsb/commit/d95c14d))
- add missing required missing flags for codecov command ([cd3cb29](https://github.com/dbbs-lab/bsb/commit/cd3cb29))
- typo and lint ([c2d4713](https://github.com/dbbs-lab/bsb/commit/c2d4713))
- drop docformatter since results does not match expectations. ([2abeb32](https://github.com/dbbs-lab/bsb/commit/2abeb32))
- drop packages and lib versions since they are installed from sources ([55932b6](https://github.com/dbbs-lab/bsb/commit/55932b6))
- lint for arborize ([cb2a66c](https://github.com/dbbs-lab/bsb/commit/cb2a66c))
- drop lib versions since they are installed from sources ([08f2d6d](https://github.com/dbbs-lab/bsb/commit/08f2d6d))
- remove verbose flag, added codecov token to bsb ([cf18f36](https://github.com/dbbs-lab/bsb/commit/cf18f36))
- attempt debug codecov upload with echo ([25e60f7](https://github.com/dbbs-lab/bsb/commit/25e60f7))
- pass secret token to build workflow ([6647b0f](https://github.com/dbbs-lab/bsb/commit/6647b0f))

### ⚠️  Breaking Changes

- ⚠️  add boolean flag when initializing Scaffold to force update the configuration ([#6](https://github.com/dbbs-lab/bsb/issues/6))

### ❤️ Thank You

- drodarie

## 6.0.0-a2 (2025-05-17)

### 🚀 Features

- add bsb-hdf5 project through nx ([aa792f2](https://github.com/dbbs-lab/bsb/commit/aa792f2))
- add bsb-arbor package ([5e89ae9](https://github.com/dbbs-lab/bsb/commit/5e89ae9))
- add bsb-json ([d661f03](https://github.com/dbbs-lab/bsb/commit/d661f03))
- add bsb-yaml ([63792fe](https://github.com/dbbs-lab/bsb/commit/63792fe))
- add bsb metapackage to monorepo ([86eba3d](https://github.com/dbbs-lab/bsb/commit/86eba3d))
- add tests with mpi ([3e71e14](https://github.com/dbbs-lab/bsb/commit/3e71e14))
- re-add github action for tests on branch ([766e6f9](https://github.com/dbbs-lab/bsb/commit/766e6f9))
- add nx target for docs ([d7446bd](https://github.com/dbbs-lab/bsb/commit/d7446bd))
- make bsb-hdf5 docs similar to other sub-packages docs ([35fcdb8](https://github.com/dbbs-lab/bsb/commit/35fcdb8))
- add GHA for documentation ([3aac975](https://github.com/dbbs-lab/bsb/commit/3aac975))
- pass on lint plus fix docs issues. ([b8db215](https://github.com/dbbs-lab/bsb/commit/b8db215))
- add bsb-nest ([7f671be](https://github.com/dbbs-lab/bsb/commit/7f671be))

### 🩹 Fixes

- first lint pass ([b93d808](https://github.com/dbbs-lab/bsb/commit/b93d808))
- second lint pass ([9bd941b](https://github.com/dbbs-lab/bsb/commit/9bd941b))
- third lint pass ([9476145](https://github.com/dbbs-lab/bsb/commit/9476145))
- fourth lint pass ([59fd189](https://github.com/dbbs-lab/bsb/commit/59fd189))
- lint on bsb-arbor ([955f6c1](https://github.com/dbbs-lab/bsb/commit/955f6c1))
- use __future__.annotation to remove deprecated typing.Union ([b6cc3b0](https://github.com/dbbs-lab/bsb/commit/b6cc3b0))
- rollback for the __all__ variable because of sphinx autodocs ([bc919e8](https://github.com/dbbs-lab/bsb/commit/bc919e8))
- lint on bsb-json and bsb-yaml ([79a8676](https://github.com/dbbs-lab/bsb/commit/79a8676))
- make tests pass ([34b1975](https://github.com/dbbs-lab/bsb/commit/34b1975))
- typos in toml files ([b503513](https://github.com/dbbs-lab/bsb/commit/b503513))
- set line-length to 90 for each sub repo and cleanup ([abad908](https://github.com/dbbs-lab/bsb/commit/abad908))
- add package-lock.json for GHA ([d8873cb](https://github.com/dbbs-lab/bsb/commit/d8873cb))
- re-add package.json ([f5c3af8](https://github.com/dbbs-lab/bsb/commit/f5c3af8))
- switch from pytest to coverage as pytest-cov does not work well with mpi ([2680dbd](https://github.com/dbbs-lab/bsb/commit/2680dbd))
- re add __all__ in __init__.py and fix sphinx autodoc ([e3cb674](https://github.com/dbbs-lab/bsb/commit/e3cb674))
- link bsb-core, bsb-json and bsb-yaml docs to main ([071bfc4](https://github.com/dbbs-lab/bsb/commit/071bfc4))
- link nx task together, use bsb-core dependencies instead of bsb main ([ae1005f](https://github.com/dbbs-lab/bsb/commit/ae1005f))
- nx task dependencies ([586a9b5](https://github.com/dbbs-lab/bsb/commit/586a9b5))
- cases when trying to remove connectivity sets that does not exist ([8691441](https://github.com/dbbs-lab/bsb/commit/8691441))
- link sphinxext-bsb to other bsb subpackages ([9a65942](https://github.com/dbbs-lab/bsb/commit/9a65942))
- run coverage command through uv ([fba8770](https://github.com/dbbs-lab/bsb/commit/fba8770))
- use nx action to retrieve head and base shas for affected ([2ecce86](https://github.com/dbbs-lab/bsb/commit/2ecce86))
- force version of python for GHA ([c588925](https://github.com/dbbs-lab/bsb/commit/c588925))
- typo in GHA ([f5b3698](https://github.com/dbbs-lab/bsb/commit/f5b3698))
- test env for GHA ([89def20](https://github.com/dbbs-lab/bsb/commit/89def20))
- bsb-core lint ([c15f561](https://github.com/dbbs-lab/bsb/commit/c15f561))
- bsb-core lint on line length ([8b7f6d4](https://github.com/dbbs-lab/bsb/commit/8b7f6d4))
- finish linting. add GHA for lint ([0d3f971](https://github.com/dbbs-lab/bsb/commit/0d3f971))
- add missing libgsl lib + minor fixes ([743fa97](https://github.com/dbbs-lab/bsb/commit/743fa97))

### ❤️ Thank You

- drodarie

## 4.1.2-0 (2025-05-17)

### 🚀 Features

- add bsb-hdf5 project through nx ([aa792f2](https://github.com/dbbs-lab/bsb/commit/aa792f2))
- add bsb-arbor package ([5e89ae9](https://github.com/dbbs-lab/bsb/commit/5e89ae9))
- add bsb-json ([d661f03](https://github.com/dbbs-lab/bsb/commit/d661f03))
- add bsb-yaml ([63792fe](https://github.com/dbbs-lab/bsb/commit/63792fe))
- add bsb metapackage to monorepo ([86eba3d](https://github.com/dbbs-lab/bsb/commit/86eba3d))
- add tests with mpi ([3e71e14](https://github.com/dbbs-lab/bsb/commit/3e71e14))
- re-add github action for tests on branch ([766e6f9](https://github.com/dbbs-lab/bsb/commit/766e6f9))
- add nx target for docs ([d7446bd](https://github.com/dbbs-lab/bsb/commit/d7446bd))
- make bsb-hdf5 docs similar to other sub-packages docs ([35fcdb8](https://github.com/dbbs-lab/bsb/commit/35fcdb8))
- add GHA for documentation ([3aac975](https://github.com/dbbs-lab/bsb/commit/3aac975))
- pass on lint plus fix docs issues. ([b8db215](https://github.com/dbbs-lab/bsb/commit/b8db215))
- add bsb-nest ([7f671be](https://github.com/dbbs-lab/bsb/commit/7f671be))

### 🩹 Fixes

- first lint pass ([b93d808](https://github.com/dbbs-lab/bsb/commit/b93d808))
- second lint pass ([9bd941b](https://github.com/dbbs-lab/bsb/commit/9bd941b))
- third lint pass ([9476145](https://github.com/dbbs-lab/bsb/commit/9476145))
- fourth lint pass ([59fd189](https://github.com/dbbs-lab/bsb/commit/59fd189))
- lint on bsb-arbor ([955f6c1](https://github.com/dbbs-lab/bsb/commit/955f6c1))
- use __future__.annotation to remove deprecated typing.Union ([b6cc3b0](https://github.com/dbbs-lab/bsb/commit/b6cc3b0))
- rollback for the __all__ variable because of sphinx autodocs ([bc919e8](https://github.com/dbbs-lab/bsb/commit/bc919e8))
- lint on bsb-json and bsb-yaml ([79a8676](https://github.com/dbbs-lab/bsb/commit/79a8676))
- make tests pass ([34b1975](https://github.com/dbbs-lab/bsb/commit/34b1975))
- typos in toml files ([b503513](https://github.com/dbbs-lab/bsb/commit/b503513))
- set line-length to 90 for each sub repo and cleanup ([abad908](https://github.com/dbbs-lab/bsb/commit/abad908))
- add package-lock.json for GHA ([d8873cb](https://github.com/dbbs-lab/bsb/commit/d8873cb))
- re-add package.json ([f5c3af8](https://github.com/dbbs-lab/bsb/commit/f5c3af8))
- switch from pytest to coverage as pytest-cov does not work well with mpi ([2680dbd](https://github.com/dbbs-lab/bsb/commit/2680dbd))
- re add __all__ in __init__.py and fix sphinx autodoc ([e3cb674](https://github.com/dbbs-lab/bsb/commit/e3cb674))
- link bsb-core, bsb-json and bsb-yaml docs to main ([071bfc4](https://github.com/dbbs-lab/bsb/commit/071bfc4))
- link nx task together, use bsb-core dependencies instead of bsb main ([ae1005f](https://github.com/dbbs-lab/bsb/commit/ae1005f))
- nx task dependencies ([586a9b5](https://github.com/dbbs-lab/bsb/commit/586a9b5))
- cases when trying to remove connectivity sets that does not exist ([8691441](https://github.com/dbbs-lab/bsb/commit/8691441))
- link sphinxext-bsb to other bsb subpackages ([9a65942](https://github.com/dbbs-lab/bsb/commit/9a65942))
- run coverage command through uv ([fba8770](https://github.com/dbbs-lab/bsb/commit/fba8770))
- use nx action to retrieve head and base shas for affected ([2ecce86](https://github.com/dbbs-lab/bsb/commit/2ecce86))
- force version of python for GHA ([c588925](https://github.com/dbbs-lab/bsb/commit/c588925))
- typo in GHA ([f5b3698](https://github.com/dbbs-lab/bsb/commit/f5b3698))
- test env for GHA ([89def20](https://github.com/dbbs-lab/bsb/commit/89def20))
- bsb-core lint ([c15f561](https://github.com/dbbs-lab/bsb/commit/c15f561))
- bsb-core lint on line length ([8b7f6d4](https://github.com/dbbs-lab/bsb/commit/8b7f6d4))
- finish linting. add GHA for lint ([0d3f971](https://github.com/dbbs-lab/bsb/commit/0d3f971))
- add missing libgsl lib + minor fixes ([743fa97](https://github.com/dbbs-lab/bsb/commit/743fa97))

### ❤️ Thank You

- drodarie

## 1.0.5 (2025-04-12)

This was a version bump only, there were no code changes.

## 1.0.4 (2025-04-12)

This was a version bump only, there were no code changes.

## 1.0.3 (2025-04-12)

This was a version bump only, there were no code changes.

## 1.0.2 (2025-04-12)

This was a version bump only, there were no code changes.

## 1.0.1 (2025-04-12)

This was a version bump only, there were no code changes.