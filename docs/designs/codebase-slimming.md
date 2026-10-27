# Codebase Slimming and Turnitout Removal

## Problem and User Outcome

The repository has accumulated redundant files, obsolete documentation notes, an
unused third-party vendor subtree, and a prototype local rule humanizer
(`turnitout`) that is no longer wanted.

The goal is to cleanly prune `turnitout`, remove unreferenced loose `.md` files
and abandoned vendor experiments, and maintain 100% test integrity and EGM
contract alignment.

## Scope of Pruning

### 1. Complete Turnitout Removal
- Remove `engine/review/turnitout.py` (the local rule replacement implementation).
- Remove `tests/test_turnitout.py` (4 test cases for Turnitout rules).
- Remove `docs/TURNITOUT.md` (untracked doc).
- Remove `vendor/turnitout-humanizer/` (entire unreferenced upstream clone, ~20+ files).
- In `engine/feedback_humanizer.py`:
  - Remove the `if mode == 'turnitout':` branch from `configured_rewriter()`.
  - Update the exception message to `"TS_HUMANIZER must be off or local."`.
- In `run_portal.py`:
  - Remove `os.environ.setdefault("TS_HUMANIZER", "turnitout")` to prevent runtime 503 crashes on startup.
- In `engine/review_runtime.py`:
  - Restrict the schema validator's allowed `humanizer` set to `{'off', 'local'}`.

### 2. Elimination of Unreferenced and Scratch Markdown Documents
- Root scratch outputs:
  - `goldfish_review_report.md`
  - `2026-10-26_DRIFT_REPORT.md`
- Loose, unreferenced documentation notes in `docs/` that duplicate canonical
  designs in `docs/designs/` or represent temporary work notes:
  - `docs/CLEVER_HUMANIZER_INTEGRATION.md` (canonical spec: `docs/designs/clever-manual-widget.md`)
  - `docs/FEEDBACK_HUMANIZER.md` (canonical spec: `docs/designs/feedback-humanizer.md`)
  - `docs/LOCAL_THINKINGSTORM_REVIEWER.md`
  - `docs/STUDIO_FEEDBACK_EDITING.md` (canonical spec: `docs/designs/studio-feedback-editing.md`)
  - `docs/STUDIO_PROGRESS.md` (canonical spec: `docs/designs/studio-review-progress.md`)
  - `docs/THINKINGSTORM_REVIEW_QUALITY.md`
  - `docs/UI_UX_ROLLOUT.md`

### 3. Removal of Abandoned Vendor Experiment Subtrees
- `vendor/blader-humanizer/`: Untracked standalone prototype (LICENSE, README.md,
  SKILL.md); completely unreferenced by production code or tests.

### 4. Preservation of Protected Components
- `vendor/humanizer/`: Kept intact. Contains `editor_prompt.txt` and prompt
  formats tested by `tests/test_feedback_humanizer.py` and used by
  `tools/start_feedback_humanizer.ps1`.
- `vendor/elephant-goldfish-model/`: Kept intact. The core EGM development
  framework.
- All functional production and operational modules in `engine/`, `portal/`,
  `bridge/`, `orchestrator/`, `outbound/`, `payments/`, `security/`, `mail/`,
  `legal/`, and `tools/`.
- All active unit test suites in `tests/`.

### 5. Contract Synchronization
- In `engine/review/EGM.md`:
  - Remove `turnitout.py` from the `Guarded humanization` section.
  - Remove the `Turnitout humanization` invariant from `Invariants`.
  - Remove `tests.test_turnitout` from `Verification`.
- In `engine/EGM.md`:
  - Remove `TurnitoutHumanizer` from `configured_rewriter()` description.
  - Remove `turnitout` from `apply_runtime_defaults()` description.
- In root `EGM.md`:
  - Remove `TS_HUMANIZER=turnitout` references.
- In `portal/EGM.md` and `tools/EGM.md`:
  - Update the test suite count from 96 to 92 passing tests.

## Alternatives Considered

1. **Keep Turnitout disabled as a dormant fallback**:
   Rejected. The user explicitly directed its removal. Dead code increases
   cognitive load and maintenance surface.
2. **Retain loose `docs/*.md` files**:
   Rejected. These files are untracked summaries of specifications already
   formalized in `docs/designs/`. Keeping parallel documentation breeds drift.
3. **Delete `vendor/humanizer/`**:
   Rejected. Unlike `turnitout` and `blader`, `vendor/humanizer/editor_prompt.txt`
   is an active fixture referenced by `tests/test_feedback_humanizer.py` and
   `tools/start_feedback_humanizer.ps1`.

## Risks and Mitigations

- **Risk: Breaking `configured_rewriter` when callers pass `turnitout`**:
  *Mitigation*: Restricting `TS_HUMANIZER` back to `off` and `local` raises
  `HumanizerUnavailable` when an invalid backend is requested, failing closed as
  designed.
- **Risk: Portal startup crash if `run_portal.py` retains `turnitout` default**:
  *Mitigation*: Explicitly removed `os.environ.setdefault("TS_HUMANIZER", "turnitout")`
  from `run_portal.py`.
- **Risk: Removing files referenced by tests**:
  *Mitigation*: Pre-verified with global cross-reference search. Full unittest
  discovery (`python -m unittest discover -s tests`) must pass cleanly with 92 tests.

## Verification Gate

1. `python -m unittest discover -s tests`: Must run 92 tests and return exit code 0.
2. `git status`: Confirm untracked sprawl is cleaned and only intentional
   modifications remain.
3. Validate all 15 EGM contracts to verify 0 broken links and 100% compliance.
