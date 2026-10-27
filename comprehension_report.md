# Stage 6: Comprehension Test Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target File**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md)
**Summary**: **0 Blockers (🔴), 0 Majors (🟡), 3 Nits (🟢)**.

---

## Findings

### 1. Clarify `ADVICE_START` Origin and Exception Message in `validate_rewrite()`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L177-L179) (`Detailed Implementation Plan — 2. engine/review/humanization.py`)
* **Discrepancy Description & Rationale**: Line 179 references `not ADVICE_START.search(plain)` without stating that `ADVICE_START` is an existing module-level regex in [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L46-L49). Additionally, explicitly stating that `STRICT_CONDITIONALS` and `UNCERTAINTY` mismatches raise the same `RejectedRewrite('negation, conditions or uncertainty changed')` exception removes any ambiguity for an implementer.

### 2. Clarify Quote-Preserving Contraction Expansion in `_normalize_prose()`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L213-L214) (`Detailed Implementation Plan — 6. portal/feedback_editor.py`)
* **Discrepancy Description & Rationale**: Line 213 imports `_expand` and `_outside_quotes` from `engine.review.humanization`, and Line 214 states that `_normalize_prose(text: str, seed: str) -> str` expands contractions outside quoted spans and runs `scrub_ai_tells(text, seed=seed)`. Because `_outside_quotes()` strips quoted spans rather than transforming text in-place, clarify that quote-preserving expansion masks quoted spans (using the same quote patterns as `anti_ai_patterns.py`), applies `_expand()` to unmasked segments, and restores the quoted spans before calling `scrub_ai_tells(text, seed=seed)`.

### 3. Align Bulk Paste DOM IDs Between `feedback-editor.js` and `studio.html`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L229) vs. [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L247) (`Detailed Implementation Plan — 7 & 9`)
* **Discrepancy Description & Rationale**: Line 229 lists `bulkCommentsToggle`, `bulkCommentsPanel`, `bulkCommentsInput`, and `applyBulkCommentsBtn`, whereas Line 247 uses `<details id="bulkCommentsPanel"><summary id="bulkCommentsToggle">...</summary>...</details>` without explicitly showing `id="bulkCommentsToggle"` on `<summary>`. Adding `id="bulkCommentsToggle"` to `<summary>` in Section 9 keeps the DOM contract 1:1.
