# 8.0.0 (2026-10-15)

### 🚀 Features

- ⚠️  **bsb-core:** recordings say what they recorded, and read_results traces it back to the network ([#293](https://github.com/dbbs-lab/bsb/pull/293), [#288](https://github.com/dbbs-lab/bsb/issues/288))
- ⚠️  **bsb-core:** a device records every cell it watched ([#290](https://github.com/dbbs-lab/bsb/pull/290))
- ⚠️  **bsb-core:** record one signal per cell, annotated the same way everywhere ([#272](https://github.com/dbbs-lab/bsb/pull/272))
- **bsb-core:** configured randomness, with replicates and reproduction ([#264](https://github.com/dbbs-lab/bsb/pull/264))
- ⚠️  **bsb-core:** parameters answer what a model's values are, per arity ([#260](https://github.com/dbbs-lab/bsb/pull/260))
- ⚠️  **bsb-core:** drop the adapter's post_prepare argument ([#278](https://github.com/dbbs-lab/bsb/pull/278))
- ⚠️  **bsb-core:** give the prepared simulation a hook of its own ([#263](https://github.com/dbbs-lab/bsb/pull/263))
- **bsb-core:** add an after_simulation hook ([#257](https://github.com/dbbs-lab/bsb/pull/257))
- Rust acceleration for segment intersection touch detection and Poisson-disk placement ([#256](https://github.com/dbbs-lab/bsb/pull/256))
- Add distribution based placement ([#242](https://github.com/dbbs-lab/bsb/pull/242))

### 🩹 Fixes

- ⚠️  **bsb-core:** multiplex per-device recordings instead of one Neo object per cell ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- ⚠️  seed postprocessing hooks and Distribution draws; require Python 3.11 ([#291](https://github.com/dbbs-lab/bsb/pull/291))
- **release:** bump sibling pins on release and stop skipping the release run ([#259](https://github.com/dbbs-lab/bsb/pull/259), [#193](https://github.com/dbbs-lab/bsb/issues/193))
- Python 3.13 and 3.14 compatibility, arbor 0.12 ([#249](https://github.com/dbbs-lab/bsb/pull/249))

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
- **bsb-core:** parameters answer what a model's values are, per arity  ([#260](https://github.com/dbbs-lab/bsb/pull/260))
  `Parameter` no longer has a `value` attribute and
  `ParameterValue` is removed. `CellModel.parameters` is a dict keyed by the model
  parameter, not a list. `constants` blocks no longer accept a computed parameter;
  write it in `parameters`. `resolution` is configured on any simulation, not only
  per backend.
- **bsb-core:** drop the adapter's post_prepare argument  ([#278](https://github.com/dbbs-lab/bsb/pull/278))
- **bsb-core:** give the prepared simulation a hook of its own  ([#263](https://github.com/dbbs-lab/bsb/pull/263))
  `post_prepare` on a simulation is replaced by `after_prepare`,
  whose entries are named dynamic nodes with a `strategy` rather than a list of
  dotted function paths.
  Claude-Session: https://claude.ai/code/session_01BHScuq1Hoemb5AUeofueWP

### ❤️ Thank You

- Claude Opus 4.6
- Claude Opus 4.8 (1M context)
- Claude Opus 5
- Claude Opus 5 (1M context)
- Claude Sonnet 5
- Dimitri Rodarie
- Dimitri RODARIE
- Filippo @filimarc
- Robin De Schepper

## 7.6.1 (2026-09-18)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.6.0 (2026-06-30)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.5.1 (2026-06-30)

This was a version bump only for bsb to align it with other projects, there were no code changes.

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

### ❤️ Thank You

- drodarie

## 7.3.0 (2026-03-20)

### 🚀 Features

- overwrite labels for ps ([#224](https://github.com/dbbs-lab/bsb/pull/224))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.3 (2026-02-21)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.2.2 (2026-02-21)

### 🩹 Fixes

- bump mpi4py and minor fixes ([#221](https://github.com/dbbs-lab/bsb/pull/221))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.1 (2026-01-19)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.2.0 (2026-01-13)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.1.0 (2026-01-09)

### 🚀 Features

- Add Class to fuse connections ([#203](https://github.com/dbbs-lab/bsb/pull/203))

### ❤️ Thank You

- Filippo @filimarc

## 7.0.3 (2025-12-17)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 7.0.2 (2025-12-12)

This was a version bump only for bsb to align it with other projects, there were no code changes.

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

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 6.0.6 (2025-08-26)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 6.0.5 (2025-08-26)

This was a version bump only for bsb to align it with other projects, there were no code changes.

## 6.0.4 (2025-07-31)

### 🩹 Fixes

- applied a fix for targeting strategies ([#164](https://github.com/dbbs-lab/bsb/pull/164))

### ❤️ Thank You

- Filippo @filimarc

## 6.0.3 (2025-07-25)

This was a version bump only for bsb to align it with other projects, there were no code changes.

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

## 6.0.0-a6 (2025-06-10)

This was a version bump only for bsb to align it with other projects, there were no code changes.