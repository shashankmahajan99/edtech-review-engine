# Agent notes for this repository

## Runtime rules

- `engine/review/` is deterministic and offline: no model calls, no network, no
  token budget. Do not add LLM or API dependencies there; the portal's optional
  model path is gated behind `APEX_ENABLE_LLM=1` and must stay optional.
- Deliverables must keep the original document intact: comments and endnotes are
  native Word parts, the redline edits `word/document.xml` in place, and the
  release gate in `engine/review/validate.py` must pass before anything ships.
- Do not regenerate fixture files or corpus snapshots unless the change requires
  it; several tests compare against them.

## Tests

```
python -m unittest discover -s tests
```

The Studio page must keep parsing: `tests/test_studio_js.py` runs `node --check`
on the rendered script.

## Design work

Architectural or multi-step features go through the vendored Elephant-Goldfish
Model: draft a specification in `docs/designs/<feature>.md`, review it with the
Goldfish personas, then implement. See `docs/EGM.md` for the skill files and
prompts. EGM is a development workflow only; it does not change runtime
behaviour.
