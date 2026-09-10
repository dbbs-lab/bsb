# CLAUDE.md

Project guidance for AI agents working in this repository.

## Project

Brain Scaffold Builder (BSB) — a component framework for multiscale bottom-up neural modeling. Python 3.10+, GPLv3.

Monorepo with Nx + uv. Published packages live in `packages/`, utility libraries in `libs/`, examples in `examples/`.

## Bootstrap & Setup

```bash
./devtools/bootstrap-linux.sh   # install uv and nodejs
uv venv && source .venv/bin/activate
uv pip install -e ./devtools    # editable install of all packages
uv run pre-commit install
```

## Common Commands

```bash
# Build / lint / test via Nx
nx run-many -t build
nx run-many -t lint
nx run-many -t test
nx test bsb-core                # single package

# Affected only (PRs)
nx affected -t test --base=origin/main --head=HEAD

# Full suite (main branch)
./nx run-many -t test

# Lint / format manually
uv run ruff check --fix
uv run ruff format

# Verify public API (required before commit)
cd packages/bsb-core && uv run tools/generate_public_api.py --check

# Build docs
nx run bsb-core:docs
```

## Tests

Tests use Python `unittest`. Each package has a `tests/` directory. bsb-core runs tests both normally and under MPI:

```bash
coverage run -p -m unittest discover -v -s ./tests
mpiexec -n 2 coverage run -p -m unittest discover -v -s ./tests
coverage combine && coverage xml
```

Set `BSB_QUIET=true` to suppress verbose output.

## MPI collectives

`bcast`, `barrier`, `gather` and `allgather` only work if **every** rank reaches
them, in the same order. A rank that arrives alone waits forever, and the run hangs
until CI's hour is up rather than failing.

**Only add a collective at a point that is already guaranteed collective.** Known
guaranteed points:

- config boot hooks — `_boot_nodes` gives every node the scaffold and wraps each
  `__boot__` in `scaffold._comm.try_all`, so all ranks are there;
- `SimulatorAdapter.simulate()` and the loops inside it, which every rank runs.

**If no guaranteed point exists for what you need, stop and say so.** Establishing a
new synchronisation point changes the framework's contract with every backend and
every component author. Raise it as a design question rather than picking a spot
that looks collective; "it happens to be called from everywhere today" is not a
guarantee.

Once you have a point, the rest:

- **Use the owning object's communicator**, never the module-level `MPI` singleton,
  whenever the object has one: `scaffold._comm`, `adapter.comm`,
  `SimulationResult.comm`. The singleton is `COMM_WORLD`, and a caller that passed a
  sub-communicator has ranks outside it that will never arrive.
- **Never put a collective in lazily reached code** — a property, a cache, an
  `is None` accessor, a `__getattr__`. Those are reached by whichever rank happens to
  need the value first. Resolve the value at the collective point and let the lazy
  path read what is already there.
- **Do not return early on per-rank state** in a function that goes on to a
  collective. Guard on something every rank computes identically, or agree on it
  first.
- **Rank-0-only work between two barriers must not be able to raise.** An exception
  there skips the second barrier and deadlocks everyone else. Wrap it in
  `try`/`finally`, or use `comm.try_all` / `comm.try_main`, which broadcast the
  exception so all ranks fail together.
- Anything drawn or generated per run — a seed, a uuid, a timestamp — is drawn once
  and broadcast. Drawn per rank, the ranks silently disagree about what run they are
  in, which surfaces much later as a deadlock somewhere unrelated.

Tests: the suite runs both serially and under `mpiexec -n 2`, so a deadlock shows up
as a 60 minute CI hang, not a failure. Do not spawn subprocesses from a rank; use
`@skip_parallel` (see `tests/test_projects.py`) or strip the `OMPI_*`/`PMI*` variables
from the child environment (see `tests/test_observability.py`).

## Code Style

Ruff v0.11.5+, line length 90, double quotes, rules: E, F, UP, B, SIM, I. Pre-commit hooks run ruff linter + formatter + conventional-pre-commit + api-test. Commit messages must follow conventional commits (`feat:`, `fix:`, `docs:`, etc.).

## Documentation style

When writing or editing any `.rst`, `.md`, or docstring, follow the
documentation conventions in `packages/bsb/docs/dev/documentation.rst`
(the "Conventions" section).

## Architecture

### Plugin System

BSB is fully plugin-based via Python entry points (`importlib.metadata.entry_points()`). Key extension points in `pyproject.toml`:

| Group | Key | Package |
|---|---|---|
| `bsb.storage.engines` | `hdf5` | bsb-hdf5 |
| `bsb.config.parsers` | `json`, `yaml` | bsb-json, bsb-yaml |
| `bsb.simulation_backends` | `nest`, `neuron`, `arbor` | bsb-nest, bsb-neuron, bsb-arbor |
| `bsb.commands` | `commands`, `projects` | bsb-core |

Plugin loading: `packages/bsb-core/bsb/plugins.py`.

### Core Abstractions (bsb-core)

- **`Scaffold`** (`bsb.core`) — top-level network object; owns configuration, storage, placement and connectivity operations
- **`Configuration`** (`bsb.config`) — describes topology, cell types, placement/connectivity rules; parsed from YAML/JSON by plugin parsers
- **`PlacementStrategy`** (`bsb.placement.strategy`) — abstract base for neuron placement; subclass and register via entry point
- **`ConnectionStrategy`** (`bsb.connectivity.strategy`) — abstract base for connectivity rules
- **`Storage`** (`bsb.storage`) — abstraction over storage backends; HDF5 backend provided by bsb-hdf5
- **Simulation adapters** (`bsb.simulation`) — thin adapter layer; each simulator backend (NEST/NEURON/ARBOR) implements it as a plugin

### Topology

Regions → Partitions → Voxels (rtree-backed spatial index). Morphologies loaded via `morphio`.

### Meta-package

`packages/bsb` is the user-facing PyPI package; it simply depends on bsb-core + bsb-hdf5 + bsb-json + bsb-yaml.

## Public API

`packages/bsb-core/bsb/__init__.py` is auto-generated by `tools/generate_public_api.py`. Modify the generator script, not `__init__.py` directly. The pre-commit `api-test` hook and `nx run bsb-core:check-api` enforce this.

## Release

Automated via Nx on push to main: `./nx release version` → `./nx release changelog` → `./nx release publish`. Semantic versioning driven by conventional commits. Publishing uses PyPI Trusted Publisher (OIDC).
