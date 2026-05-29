# BSB Monorepo Package Boilerplate

## Directory Structure

```
packages/bsb-{name}/
  bsb_{name}/          # Main module (underscore, not hyphen)
    __init__.py
  docs/
  tests/
  pyproject.toml
  project.json
  README.md
  CHANGELOG.md
  LICENSE
  uv.lock
```

Exception: `bsb-core` uses `bsb/` as the module dir (not `bsb_core/`).

---

## pyproject.toml

```toml
[build-system]
requires = ["flit_core>=3.2,<4"]
build-backend = "flit_core.buildapi"

[project]
name = "bsb-{name}"
version = "7.2.3"           # keep in sync with monorepo
readme = "README.md"
requires-python = ">=3.10,<4"
dynamic = ["description"]
classifiers = [
  "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)"
]

[[project.authors]]
name = "Robin De Schepper"
email = "robin@alexandria.sc"

[[project.authors]]
name = "Dimitri Rodarie"
email = "dimitri.rodarie@unipv.it"

[project.license]
file = "LICENSE"

[project.dependencies]
# package-specific

# Entry points vary by package type:
# storage engine:         [project.entry-points."bsb.storage.engines"]
# config parser:          [project.entry-points."bsb.config.parsers"]
# config template:        [project.entry-points."bsb.config.templates"]
# simulation backend:     [project.entry-points."bsb.simulation_backends"]

[dependency-groups]
test = [
  "bsb-core[parallel]",
  "bsb-test~=7.0",
  "coverage>=7.3",
]
docs = [
  "furo~=2024.0",
  "sphinxext-bsb~=7.0",
]
dev = [
  "pre-commit~=3.5",
  "ruff>=0.8.2",
]

[tool.uv]
default-groups = ["dev", "docs", "test"]

[tool.uv.sources]
bsb-core = { path = "../bsb-core", editable = true }
bsb-test = { path = "../bsb-test", editable = true }
# add other internal deps as needed

[tool.flit.module]
name = "bsb_{name}"

[tool.coverage.run]
branch = true
source = ["bsb_{name}"]

[tool.coverage.report]
exclude_lines = ["if typing.TYPE_CHECKING:", "pragma: nocover"]
show_missing = true

[tool.ruff]
exclude = [".ruff_cache", ".svn", ".tox", ".venv", "dist"]
line-length = 90
indent-width = 4

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"
docstring-code-format = true
docstring-code-line-length = 90

[tool.ruff.lint]
select = ["E", "F", "UP", "B", "SIM", "I"]
ignore = []
fixable = ["ALL"]
unfixable = []
```

---

## project.json (Nx)

```json
{
  "name": "bsb-{name}",
  "$schema": "../../.nx/installation/node_modules/nx/schemas/project-schema.json",
  "projectType": "library",
  "sourceRoot": "packages/bsb-{name}/bsb_{name}",
  "targets": {
    "lock":   { "executor": "@nxlv/python:lock" },
    "sync":   { "executor": "@nxlv/python:sync" },
    "add":    { "executor": "@nxlv/python:add" },
    "update": { "executor": "@nxlv/python:update" },
    "remove": { "executor": "@nxlv/python:remove" },
    "build": {
      "executor": "@nxlv/python:build",
      "outputs": ["{workspaceRoot}/dist/bsb-{name}"],
      "options": { "outputPath": "dist/bsb-{name}", "publish": false }
    },
    "lint": {
      "executor": "@nxlv/python:ruff",
      "options": { "lintFilePatterns": ["bsb_{name}", "tests"] }
    },
    "format": {
      "executor": "@nxlv/python:ruff-format",
      "options": { "filePatterns": ["bsb_{name}", "tests"] }
    },
    "test": {
      "executor": "nx:run-commands",
      "options": {
        "commands": [
          "uv run coverage run -m unittest discover -s ./tests",
          "mpiexec -n 2 uv run coverage run -p -m unittest discover -s ./tests"
        ],
        "parallel": false,
        "cwd": "packages/bsb-{name}"
      }
    },
    "iso-docs": {
      "executor": "nx:run-commands",
      "options": {
        "command": "uv run sphinx-build -b html docs docs/_build/iso-html",
        "cwd": "packages/bsb-{name}"
      }
    },
    "docs": {
      "executor": "nx:run-commands",
      "dependsOn": ["bsb-core:iso-docs"],
      "options": {
        "command": "uv run sphinx-build -b html docs docs/_build/html",
        "cwd": "packages/bsb-{name}"
      }
    },
    "install": {
      "executor": "@nxlv/python:install",
      "options": { "silent": false, "args": "", "cwd": "packages/bsb-{name}" }
    },
    "nx-release-publish": {
      "executor": "@nxlv/python:publish",
      "options": { "packageRoot": "dist/bsb-{name}" }
    }
  },
  "release": {
    "version": { "generator": "@nxlv/python:release-version" }
  }
}
```

---

## Entry Point Examples

| Package type       | Entry point group                  | Key           | Value                          |
|--------------------|------------------------------------|---------------|--------------------------------|
| Storage engine     | `bsb.storage.engines`              | e.g. `hdf5`   | `bsb_hdf5.storage_engine:HDF5` |
| Config parser      | `bsb.config.parsers`               | e.g. `json`   | `bsb_json.parser:JsonParser`   |
| Config template    | `bsb.config.templates`             | e.g. `json`   | `bsb_json.templates`           |
| Simulation backend | `bsb.simulation_backends`          | e.g. `arbor`  | `bsb_arbor.adapter:ArborAdapter` |

---

## Notes

- All packages use **unittest** (not pytest)
- Tests live in `tests/`, discovered with `unittest discover -s ./tests`
- MPI tests run with `mpiexec -n 2`
- Coverage is run in parallel mode and combined at workspace level
- Build backend is **flit** for all plugin packages; **setuptools** only for the meta-package `bsb`
- Versioning is monorepo-synchronized (currently `7.2.3`)