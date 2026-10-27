# Stage 5: Initial Zoom Out Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target File**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md)
**Summary**: **0 Blockers (🔴), 2 Majors (🟡), 1 Nit (🟢)**.

---

## Findings

### 1. Consolidate Contraction Expansion into `scrub_ai_tells()` Instead of Adding `_normalize_prose()` in `portal/feedback_editor.py`
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L163-L170) & [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L217) (`Detailed Implementation Plan — 1. engine/review/anti_ai_patterns.py & 6. portal/feedback_editor.py`)
* **Simplicity Rationale**:
  - Section 6 proposes importing private helpers [`_expand`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L39-L43) and [`_outside_quotes`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L73) from `engine.review.humanization` into [`portal/feedback_editor.py`](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py) and creating a new `_normalize_prose(text: str, seed: str) -> str` helper.
  - However, [`_outside_quotes()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L73) in `humanization.py` deletes quoted substrings (`re.sub(..., '', text)`) rather than masking and restoring them, whereas [`scrub_ai_tells()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L96-L136) in `engine/review/anti_ai_patterns.py` already masks URLs, double quotes, and apostrophe-safe single quotes via [`_mask_protected_spans()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L66-L86) and restores them via [`_unmask_protected_spans()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L89-L93).
  - **Recommendation**: Expand contractions directly inside `scrub_ai_tells()` in [`engine/review/anti_ai_patterns.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py) (replacing the removed contraction-injection pass with contraction expansion on `masked`). This makes `scrub_ai_tells()` the single canonical 0%-contraction and anti-AI normalizer across offline generation, `humanization.py`, and `portal/feedback_editor.py`, and reuse [`is_endnote_heading()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/letter_format.py#L17-L25) from `engine.review.letter_format` (already imported in `portal/feedback_editor.py`) when identifying narrative endnote paragraphs on save.

### 2. Share Apostrophe-Safe Single-Quote Handling with `engine/review/humanization.py`
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L163-L183) (`Detailed Implementation Plan — 1. engine/review/anti_ai_patterns.py & 2. engine/review/humanization.py`)
* **Simplicity Rationale**:
  - Section 1 fixes [`_TYPO_SINGLE_QUOTE_PATTERN`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L14) in `anti_ai_patterns.py` so single-quoted student excerpts containing internal apostrophes (`‘In today’s world...’`) are not truncated at the apostrophe.
  - However, [`FACTS`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L17-L23), [`_outside_quotes()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L73), and `quotes` in [`validate_rewrite()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L116) in `engine/review/humanization.py` still use `‘[^’]*’`.
  - **Recommendation**: Reuse the apostrophe-safe single-quote pattern in `engine/review/humanization.py` (`FACTS`, `_outside_quotes`, and `quotes`) so quote boundary detection is consistent across both modules.

### 3. Remove Unused `bulkCommentsToggle` Control from `portal/static/feedback-editor.js` Plan
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L229-L250) (`Detailed Implementation Plan — 7 & 9`)
* **Simplicity Rationale**:
  - Section 9 uses a native HTML `<details class="bulk-paste-panel" id="bulkCommentsPanel"><summary>Paste humanized comments block</summary>...</details>`, which handles expand/collapse natively in the browser without JavaScript. Remove `bulkCommentsToggle` from Section 7 so the JS controller only wires `bulkCommentsPanel`, `bulkCommentsInput`, and `applyBulkCommentsBtn`.
