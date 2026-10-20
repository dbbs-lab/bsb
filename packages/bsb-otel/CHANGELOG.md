## 8.0.2 (2026-10-20)

### 🩹 Fixes

- **release:** install @nxlv/python as the @helveg/nx-python fork ([#303](https://github.com/dbbs-lab/bsb/pull/303))

### ❤️ Thank You

- Claude Opus 4.8
- Robin De Schepper

## 8.0.1 (2026-10-20)

### 🩹 Fixes

- **release:** publish packages whose sibling pins carry extras or markers ([#301](https://github.com/dbbs-lab/bsb/pull/301))

### ❤️ Thank You

- Claude Opus 5.5
- Dimitri RODARIE

# 8.0.0 (2026-10-15)

### 🚀 Features

- Rust acceleration for segment intersection touch detection and Poisson-disk placement ([#256](https://github.com/dbbs-lab/bsb/pull/256))
- numpy 2.x compatibility ([#240](https://github.com/dbbs-lab/bsb/pull/240))

### 🩹 Fixes

- ⚠️  seed postprocessing hooks and Distribution draws; require Python 3.11 ([#291](https://github.com/dbbs-lab/bsb/pull/291))
- **release:** bump sibling pins on release and stop skipping the release run ([#259](https://github.com/dbbs-lab/bsb/pull/259), [#193](https://github.com/dbbs-lab/bsb/issues/193))
- Python 3.13 and 3.14 compatibility, arbor 0.12 ([#249](https://github.com/dbbs-lab/bsb/pull/249))

### ⚠️  Breaking Changes

- seed postprocessing hooks and Distribution draws; require Python 3.11  ([#291](https://github.com/dbbs-lab/bsb/pull/291))
  BSB requires Python 3.11 or newer. Every package's
  `requires-python` moves from `>=3.10,<4` to `>=3.11,<4`.

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

This was a version bump only for bsb-otel to align it with other projects, there were no code changes.

## 7.6.0 (2026-06-30)

### 🚀 Features

- **bsb-hdf5:** batched HDF5 handle scopes, job-pool dependency fixes, and connect-job tracing ([#250](https://github.com/dbbs-lab/bsb/pull/250), [#223](https://github.com/dbbs-lab/bsb/issues/223), [#1](https://github.com/dbbs-lab/bsb/issues/1))

### ❤️ Thank You

- Robin De Schepper

## 7.5.1 (2026-06-30)

This was a version bump only for bsb-otel to align it with other projects, there were no code changes.

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