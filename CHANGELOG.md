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