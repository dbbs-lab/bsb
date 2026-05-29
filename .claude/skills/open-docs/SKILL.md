---
name: open-docs
description: Build the BSB Sphinx documentation for a package and open the resulting index.html in the user's default browser. Use when the user asks to "open the docs", "build the docs", "preview the docs", "view the docs", or wants to check how a rst/docstring change renders. Defaults to the `bsb` (user-facing) package; can target any sister package (`bsb-core`, `bsb-hdf5`, `bsb-nest`, `bsb-neuron`, `bsb-arbor`, `bsb-json`, `bsb-yaml`, `bsb-test`).
---

# Build & open BSB docs

End-to-end: pick the right nx target, build the Sphinx site, open the produced `index.html` in the Windows default browser.

## When to use

- User says "open the docs", "build the docs", "preview the docs", "view the docs", "render the docs"
- User asks how a doc edit looks rendered
- User wants to inspect Sphinx output of a specific BSB package

## Bootstrap

Confirm prerequisites (one-time per session is plenty — they don't change mid-session):

- Node + npm: `node --version` (nx needs them)
- `uv` available: the nx docs targets shell out to `uv run sphinx-build`. `uv` is usually installed at `$HOME/.local/bin/uv`, which may not be on a non-interactive shell's PATH — check with `command -v uv || ls "$HOME/.local/bin/uv"`, and prepend its directory to PATH when invoking nx (see Run).
- Working directory: a checkout of `dbbs-lab/bsb`. Resolve its root with `git rev-parse --show-toplevel`; it may be the main checkout or a worktree under `.claude/worktrees/`.

If the user invoked you from a specific worktree (cwd starts with `.claude/worktrees/`), build *there* — that's where their edits live. Otherwise build from the main checkout.

## Pick the package and the target

Two nx targets per package:

| Target | Output | Use when |
|---|---|---|
| `iso-docs` | `<pkg>/docs/_build/iso-html/index.html` | Fast (single package). Cross-references to sister packages render as raw text. Default. |
| `docs` | `<pkg>/docs/_build/html/index.html` | Builds every sister package's `iso-docs` first, then the target package with full intersphinx cross-linking. Slow. |

Default to **`bsb:iso-docs`** unless:
- User explicitly asks for the cross-linked / full / production docs → use `<pkg>:docs`
- User edited docs in `bsb-core` / `bsb-hdf5` / another sister package → use `<that-pkg>:iso-docs`
- User says "all docs" or "full docs" → use `bsb:docs` (the umbrella target)

## Run

From the repo root (or worktree root), with uv's directory on PATH:

```bash
PATH="$HOME/.local/bin:$PATH" bash nx run <pkg>:<target>
```

(`$HOME/.local/bin` is uv's default install dir; adjust if `command -v uv` reports it elsewhere.) The `nx` shim in the repo root is a bash script (the wrapper is named `./nx` but bears no exec bit on the WSL share — invoke as `bash nx` or `bash ./nx`).

Notes:
- `nx run bsb:docs` requires `BSB_LOCAL_INTERSPHINX_ONLY=true` (already set by the project.json target). Don't override.
- Sphinx writes warnings; the `docs` target uses `-nW` (warnings as errors). If `nx run bsb:docs` fails on a warning, prefer `iso-docs` while diagnosing.
- Build is cached by nx; re-running without source changes is fast.

## Open the index

The build output is a WSL path; convert it to a Windows path with `wslpath -w`, then hand that to PowerShell's `Start-Process` (it launches UNC paths in the default browser reliably). First derive the Windows path in the build's WSL shell:

```bash
wslpath -w "$(git rev-parse --show-toplevel)/packages/<pkg>/docs/_build/iso-html/index.html"
```

Then launch it (use the exact string `wslpath` printed):

```powershell
Start-Process "<windows-path-from-wslpath>"
```

For the full-docs target swap `iso-html` → `html`. To jump straight to a page the user just edited, point at it directly (e.g. `.../docs/_build/html/interfaces/storage-engines.html`).

Do NOT use `cmd.exe /c start "" "\\wsl.localhost\..."` — `cmd` rejects UNC paths as the working directory and, despite the "Defaulting to Windows directory" notice, the browser often does not actually launch. `Start-Process` is the reliable path.

## Verify

After build:
- Confirm `_build/iso-html/index.html` (or `_build/html/index.html`) exists.
- Spot-check any rst page the user just edited rendered — e.g. `_build/iso-html/core/storage.html`, `_build/iso-html/simulation/intro.html`, `_build/iso-html/dev/plugins.html`.
- Then launch the browser.

Report to the user: which target was built, where the index lives, and that the browser was launched. Don't re-launch on every follow-up rebuild unless asked — let them refresh the open tab.
