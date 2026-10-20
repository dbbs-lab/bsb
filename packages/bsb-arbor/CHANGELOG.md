## 8.0.1 (2026-10-20)

### 🩹 Fixes

- **release:** publish packages whose sibling pins carry extras or markers ([#301](https://github.com/dbbs-lab/bsb/pull/301))

### ❤️ Thank You

- Claude Opus 5.5
- Dimitri RODARIE

# 8.0.0 (2026-10-15)

### 🚀 Features

- ⚠️  **bsb-core:** recordings say what they recorded, and read_results traces it back to the network ([#293](https://github.com/dbbs-lab/bsb/pull/293), [#288](https://github.com/dbbs-lab/bsb/issues/288))
- ⚠️  **bsb-core:** a device records every cell it watched ([#290](https://github.com/dbbs-lab/bsb/pull/290))
- ⚠️  **bsb-core:** record one signal per cell, annotated the same way everywhere ([#272](https://github.com/dbbs-lab/bsb/pull/272))
- ⚠️  **bsb-core:** a run ends with one results file, whatever it took to make it ([#266](https://github.com/dbbs-lab/bsb/pull/266))
- Rust acceleration for segment intersection touch detection and Poisson-disk placement ([#256](https://github.com/dbbs-lab/bsb/pull/256))
- numpy 2.x compatibility ([#240](https://github.com/dbbs-lab/bsb/pull/240))

### 🩹 Fixes

- ⚠️  **bsb-core:** multiplex per-device recordings instead of one Neo object per cell ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- ⚠️  seed postprocessing hooks and Distribution draws; require Python 3.11 ([#291](https://github.com/dbbs-lab/bsb/pull/291))
- ⚠️  **bsb-arbor:** draw the poisson generators from the network's randomness ([#280](https://github.com/dbbs-lab/bsb/pull/280))
- **release:** bump sibling pins on release and stop skipping the release run ([#259](https://github.com/dbbs-lab/bsb/pull/259), [#193](https://github.com/dbbs-lab/bsb/issues/193))
- Python 3.13 and 3.14 compatibility, arbor 0.12 ([#249](https://github.com/dbbs-lab/bsb/pull/249))
- ⚠️  Let writing data to file at flush ([#213](https://github.com/dbbs-lab/bsb/pull/213))

### ⚠️  Breaking Changes

- **bsb-core:** multiplex per-device recordings instead of one Neo object per cell  ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- seed postprocessing hooks and Distribution draws; require Python 3.11  ([#291](https://github.com/dbbs-lab/bsb/pull/291))
  BSB requires Python 3.11 or newer. Every package's
  `requires-python` moves from `>=3.10,<4` to `>=3.11,<4`.
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
- **bsb-arbor:** draw the poisson generators from the network's randomness  ([#280](https://github.com/dbbs-lab/bsb/pull/280))
- Let writing data to file at flush  ([#213](https://github.com/dbbs-lab/bsb/pull/213))

### ❤️ Thank You

- Claude Opus 4.6
- Claude Opus 4.8 (1M context)
- Claude Opus 5
- Claude Opus 5 (1M context)
- Claude Sonnet 4.6
- Claude Sonnet 5
- Dimitri RODARIE
- Filippo @filimarc
- Robin De Schepper

## 7.6.1 (2026-09-18)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.6.0 (2026-06-30)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.5.1 (2026-06-30)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

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

- Nest installation with Nx ([4bd2458](https://github.com/dbbs-lab/bsb/commit/4bd2458))
- Loading modules to check NEST models ([#228](https://github.com/dbbs-lab/bsb/pull/228))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

## 7.3.0 (2026-03-20)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.2.3 (2026-02-21)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.2.2 (2026-02-21)

### 🩹 Fixes

- bump mpi4py and minor fixes ([#221](https://github.com/dbbs-lab/bsb/pull/221))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.1 (2026-01-19)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.2.0 (2026-01-13)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.1.0 (2026-01-09)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.0.3 (2025-12-17)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 7.0.2 (2025-12-12)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

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

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 6.0.6 (2025-08-26)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

## 6.0.5 (2025-08-26)

This was a version bump only for bsb-arbor to align it with other projects, there were no code changes.

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

## [v4.1.1] - 2025-01-07
### :bug: Bug Fixes
- [`f7de054`](https://github.com/dbbs-lab/bsb-arbor/commit/f7de054c985ea1f41f81117e9951f35c558c700a) - BSB version dependencies *(PR [#5](https://github.com/dbbs-lab/bsb-arbor/pull/5) by [@drodarie](https://github.com/drodarie))*


## [v4.1.0] - 2024-08-28
### :sparkles: New Features
- [`290b136`](https://github.com/dbbs-lab/bsb-arbor/commit/290b136d47443b1357891463b5331f7f6dd38dfb) - add auto release pipeline *(PR [#4](https://github.com/dbbs-lab/bsb-arbor/pull/4) by [@drodarie](https://github.com/drodarie))*

### :bug: Bug Fixes
- [`7a4fd1c`](https://github.com/dbbs-lab/bsb-arbor/commit/7a4fd1ccf40de2484d9aa351578c36de4f378370) - bump arbor version to 0.10 *(PR [#3](https://github.com/dbbs-lab/bsb-arbor/pull/3) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#878](https://github.com/dbbs-lab/bsb-core/issues/878) opened by [@drodarie](https://github.com/drodarie)*


## [v4.0.0]
### What's Changed
* Add CI and beta deps by @Helveg in https://github.com/dbbs-lab/bsb-arbor/pull/1

### New Contributors
* @Helveg made their first contribution in https://github.com/dbbs-lab/bsb-arbor/pull/1

**Full Changelog**: https://github.com/dbbs-lab/bsb-arbor/commits/v4.0.0

[v4.1.0]: https://github.com/dbbs-lab/bsb-arbor/compare/v4.0.0...v4.1.0
[v4.1.1]: https://github.com/dbbs-lab/bsb-arbor/compare/v4.1.0...v4.1.1
