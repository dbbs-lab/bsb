## 6.0.3 (2025-07-25)

This was a version bump only for bsb-hdf5 to align it with other projects, there were no code changes.

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


## [v5.0.4] - 2025-03-03
### :bug: Bug Fixes
- [`a040a77`](https://github.com/dbbs-lab/bsb-hdf5/commit/a040a774ac8d407a626f2bdfa3805dd15e9869f3) - update stats linked to connectivity and placement sets when clearing *(PR [#41](https://github.com/dbbs-lab/bsb-hdf5/pull/41) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *fixes issue [#798](https://github.com/dbbs-lab/bsb-core/issues/798) opened by [@Helveg](https://github.com/Helveg)*


## [v5.0.3] - 2025-02-17
### :bug: Bug Fixes
- [`578f3e3`](https://github.com/dbbs-lab/bsb-hdf5/commit/578f3e3242f87d2214820d4a4582d83cc1f83471) - add handles *(PR [#38](https://github.com/dbbs-lab/bsb-hdf5/pull/38) by [@drodarie](https://github.com/drodarie))*


## [v5.0.2] - 2025-01-07
### :bug: Bug Fixes
- [`7bbe9b6`](https://github.com/dbbs-lab/bsb-hdf5/commit/7bbe9b6cf087719dd2c821102269c44ae018fffe) - typos in GHA for releases. *(commit by [@drodarie](https://github.com/drodarie))*


## [v5.0.0] - 2025-01-07
### :boom: BREAKING CHANGES
- due to [`7a89d49`](https://github.com/dbbs-lab/bsb-hdf5/commit/7a89d4921173ac0dd058c7c19a0286c785345a45) - mpi hdf5 *(PR [#36](https://github.com/dbbs-lab/bsb-hdf5/pull/36) by [@drodarie](https://github.com/drodarie))*:

  mpi hdf5 (#36)


### :recycle: Refactors
- [`7a89d49`](https://github.com/dbbs-lab/bsb-hdf5/commit/7a89d4921173ac0dd058c7c19a0286c785345a45) - mpi hdf5 *(PR [#36](https://github.com/dbbs-lab/bsb-hdf5/pull/36) by [@drodarie](https://github.com/drodarie))*
  - :arrow_lower_right: *addresses issue [#16](https://github.com/dbbs-lab/bsb-hdf5/issues/16) opened by [@Helveg](https://github.com/Helveg)*
  - :arrow_lower_right: *addresses issue [#893](https://github.com/dbbs-lab/bsb-core/issues/893) opened by [@drodarie](https://github.com/drodarie)*


## [v4.1.1] - 2024-10-23
### :bug: Bug Fixes
- [`ce29533`](https://github.com/dbbs-lab/bsb-hdf5/commit/ce29533c5479bf296c98af45b16bfe1d5ef29d3d) - forward mpi comm to lock system *(PR [#34](https://github.com/dbbs-lab/bsb-hdf5/pull/34) by [@drodarie](https://github.com/drodarie))*


## [v4.1.0] - 2024-10-08
### :sparkles: New Features
- [`9d04d60`](https://github.com/dbbs-lab/bsb-hdf5/commit/9d04d60eced939ed3e313ac8834439a98939f5e2) - implement auto-release GHA and conventional commits. *(PR [#33](https://github.com/dbbs-lab/bsb-hdf5/pull/33) by [@drodarie](https://github.com/drodarie))*

[v4.1.0]: https://github.com/dbbs-lab/bsb-hdf5/compare/v4.0.0...v4.1.0
[v4.1.1]: https://github.com/dbbs-lab/bsb-hdf5/compare/v4.1.0...v4.1.1
[v5.0.0]: https://github.com/dbbs-lab/bsb-hdf5/compare/v4.1.1...v5.0.0
[v5.0.2]: https://github.com/dbbs-lab/bsb-hdf5/compare/v5.0.1...v5.0.2
[v5.0.3]: https://github.com/dbbs-lab/bsb-hdf5/compare/v5.0.2...v5.0.3
[v5.0.4]: https://github.com/dbbs-lab/bsb-hdf5/compare/v5.0.3...v5.0.4
