# Vendored: Elephant-Goldfish Model (EGM)

- Upstream: https://github.com/google/elephant-goldfish-model
- Commit: `3d0b34821ce88ad328b0c9bf0e06d7eb5f1cd669` (2026-10-23)
- Plugin manifest: `plugin.json` — `egm` v0.1.0, Apache-2.0
- Vendored: 2026-10-25

This is Google's open-source **spec-driven development plugin**, not a runtime
model. It contains agent skills (`skills/`), Goldfish reviewer personas
(`agents/`), document standards (`resources/`) and the architecture docs
(`docs/`). It performs no inference on its own; a coding agent reads the skill
files.

## What was removed from the upstream checkout

`.git/`, `site/` (Astro marketing site), `tests/` and `.github/` were dropped to
keep the vendored copy small. `site/package-lock.json` alone was larger than the
rest of the plugin. Nothing under `skills/`, `agents/`, `resources/`, `docs/` or
the manifests was modified.

## Updating

```
git clone --depth 1 https://github.com/google/elephant-goldfish-model /tmp/egm
# copy skills/ agents/ resources/ docs/ plugin.json LICENSE README.md
# update the commit hash above
```

License: Apache-2.0, see `LICENSE` in this directory. This is not an officially
supported Google product.
