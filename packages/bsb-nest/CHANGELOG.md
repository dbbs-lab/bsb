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
- ⚠️  **bsb-nest:** seed the kernel from the network's randomness ([#275](https://github.com/dbbs-lab/bsb/pull/275))
- ⚠️  **bsb-core:** parameters answer what a model's values are, per arity ([#260](https://github.com/dbbs-lab/bsb/pull/260))
- ⚠️  **bsb-core:** drop the adapter's post_prepare argument ([#278](https://github.com/dbbs-lab/bsb/pull/278))
- ⚠️  **bsb-core:** give the prepared simulation a hook of its own ([#263](https://github.com/dbbs-lab/bsb/pull/263))
- Rust acceleration for segment intersection touch detection and Poisson-disk placement ([#256](https://github.com/dbbs-lab/bsb/pull/256))

### 🩹 Fixes

- ⚠️  **bsb-core:** multiplex per-device recordings instead of one Neo object per cell ([#297](https://github.com/dbbs-lab/bsb/pull/297))
- ⚠️  seed postprocessing hooks and Distribution draws; require Python 3.11 ([#291](https://github.com/dbbs-lab/bsb/pull/291))
- **bsb-nest:** install NEST without a synced environment ([#279](https://github.com/dbbs-lab/bsb/pull/279))
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
- **bsb-nest:** seed the kernel from the network's randomness  ([#275](https://github.com/dbbs-lab/bsb/pull/275))
  `seed` is no longer configured on a NEST simulation. Pin the
  network's `rng.seed`, or declare an `rng.settings` entry of strategy `nest` and
  name it on the simulation's `rng`.
  Claude-Session: https://claude.ai/code/session_017Zcwom5VRiA5WMreKncmVg
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
- Let writing data to file at flush  ([#213](https://github.com/dbbs-lab/bsb/pull/213))

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

### 🩹 Fixes

- **bsb-nest:** version-guarded NESTErrors import for NEST 3.10 compatibility | add packaging 26.2+ compatibility ([#287](https://github.com/dbbs-lab/bsb/pull/287))

### ❤️ Thank You

- Filippo @filimarc

## 7.6.0 (2026-06-30)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

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

- Nest installation with Nx ([4bd2458](https://github.com/dbbs-lab/bsb/commit/4bd2458))
- Loading modules to check NEST models ([#228](https://github.com/dbbs-lab/bsb/pull/228))

### ❤️ Thank You

- Dimitri RODARIE
- drodarie

## 7.3.0 (2026-03-20)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 7.2.3 (2026-02-21)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 7.2.2 (2026-02-21)

### 🩹 Fixes

- bump mpi4py and minor fixes ([#221](https://github.com/dbbs-lab/bsb/pull/221))

### ❤️ Thank You

- Dimitri RODARIE

## 7.2.1 (2026-01-19)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 7.2.0 (2026-01-13)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 7.1.0 (2026-01-09)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 7.0.3 (2025-12-17)

### 🩹 Fixes

- CLI simulate and ExtNestDevice ([#207](https://github.com/dbbs-lab/bsb/pull/207), [#204](https://github.com/dbbs-lab/bsb/issues/204), [#206](https://github.com/dbbs-lab/bsb/issues/206))

### ❤️ Thank You

- Dimitri RODARIE

## 7.0.2 (2025-12-12)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

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

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 6.0.6 (2025-08-26)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 6.0.5 (2025-08-26)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 6.0.4 (2025-07-31)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

## 6.0.3 (2025-07-25)

This was a version bump only for bsb-nest to align it with other projects, there were no code changes.

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

## [v4.3.2] - 2025-01-07
### :bug: Bug Fixes
- [`3500ecc`](https://github.com/dbbs-lab/bsb-nest/commit/3500eccc0c67fa686e1a7e0b973d4a5653fce2d6) - BSB version dependencies *(PR [#17](https://github.com/dbbs-lab/bsb-nest/pull/17) by [@drodarie](https://github.com/drodarie))*


## [v4.3.1] - 2024-11-19
### :bug: Bug Fixes
- [`d546cb5`](https://github.com/dbbs-lab/bsb-nest/commit/d546cb5700e4554367ede9ea3c60862cf0dcec54) - let multimeter split analog signals for every cell *(PR [#15](https://github.com/dbbs-lab/bsb-nest/pull/15) by [@filimarc](https://github.com/filimarc))*


## [v4.3.0] - 2024-10-07
### :sparkles: New Features
- [`8e4908a`](https://github.com/dbbs-lab/bsb-nest/commit/8e4908a13c1cc0c0b02cb80992f226a56981814f) - add sinusoidal generator and receptor_type attr *(PR [#12](https://github.com/dbbs-lab/bsb-nest/pull/12) by [@marialauradeg98](https://github.com/marialauradeg98))*

### :bug: Bug Fixes
- [`f2b58a6`](https://github.com/dbbs-lab/bsb-nest/commit/f2b58a63b98e7c81d25028d0f2c28d3bf342d7a3) - modify condition to manually bump version with GHA. *(PR [#14](https://github.com/dbbs-lab/bsb-nest/pull/14) by [@filimarc](https://github.com/filimarc))*
- [`e31f7f9`](https://github.com/dbbs-lab/bsb-nest/commit/e31f7f9c75088bd185d81be0994601e141930149) - remove condition on main GHA *(commit by [@drodarie](https://github.com/drodarie))*


## [v4.2.1] - 2024-08-14
### :bug: Bug Fixes
- [`250b5c7`](https://github.com/dbbs-lab/bsb-nest/commit/250b5c757089bf02e88ab2b34250cb152a4816d6) - Empty connection sets *(PR [#10](https://github.com/dbbs-lab/bsb-nest/pull/10) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#9](https://github.com/dbbs-lab/bsb-nest/issues/9) opened by [@drodarie](https://github.com/drodarie)*


## [v4.2.0] - 2024-08-14
### :sparkles: New Features
- [`a2a3656`](https://github.com/dbbs-lab/bsb-nest/commit/a2a3656e89333aae9d33d6a8c59deaccbcbad670) - add auto release *(PR [#11](https://github.com/dbbs-lab/bsb-nest/pull/11) by [@drodarie](https://github.com/drodarie))*


## v4.1.0

### What's Changed
* Feature/randomness by @drodarie in https://github.com/dbbs-lab/bsb-nest/pull/7
* Feature/devices by @drodarie in https://github.com/dbbs-lab/bsb-nest/pull/5

### New Contributors
* @drodarie made their first contribution in https://github.com/dbbs-lab/bsb-nest/pull/7

**Full Changelog**: https://github.com/dbbs-lab/bsb-nest/compare/v4.0.0...v4.1.0

[v4.2.0]: https://github.com/dbbs-lab/bsb-nest/compare/v4.1.0...v4.2.0
[v4.2.1]: https://github.com/dbbs-lab/bsb-nest/compare/v4.2.0...v4.2.1
[v4.3.0]: https://github.com/dbbs-lab/bsb-nest/compare/v4.2.1...v4.3.0
[v4.3.1]: https://github.com/dbbs-lab/bsb-nest/compare/v4.3.0...v4.3.1
[v4.3.2]: https://github.com/dbbs-lab/bsb-nest/compare/v4.3.1...v4.3.2
