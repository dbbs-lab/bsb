# CLAUDE.md

Project guidance for AI agents working in this repository.

## Documentation style

The canonical doc-writing conventions live in
`packages/bsb/docs/dev/documentation.rst` (the "Conventions" section). Read and
follow them before writing or editing any `.rst`, `.md`, or docstring. Key
house rules:

- No em dashes, and no en dashes outside numeric ranges. Use a colon, period,
  comma, or parentheses, or rewrite. This includes `---` in prose, which Sphinx
  auto-converts to an em dash.
- Do not reference development history in committed text (no issue numbers, no
  "introduced for X", no "as part of the Y migration") in docs, docstrings, or
  comments. The only exception is a regression-test docstring naming the bug it
  guards.
- Write "the BSB", not "BSB", in flowing prose.

Mechanical check: before declaring any doc or docstring edit done, grep the
files you touched for `—` and `–` and rewrite each occurrence.

## Building docs

Docs are built with warnings-as-errors (`sphinx-build -nW`). A warning fails CI.
The `open-docs` skill builds and previews a package; otherwise build a single
package fast with its `iso-docs` nx target, or the full cross-linked site with
the package's `docs` target.
