# Stage 8: Intermediate Zoom Out Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target File**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L1-L279) (`1..279`)
**Cross-Checked Reports**: [zoom_out_report.md](file:///C:/Users/shashank/edtech-review-engine/zoom_out_report.md) (Stage 5) & [critic_report.md](file:///C:/Users/shashank/edtech-review-engine/critic_report.md) (Stage 7)
**Summary**: **0 Blockers (🔴), 2 Majors (🟡), 2 Nits (🟢)**.

---

## 1. Cross-Check of Stage 5 & Stage 7 Recommendations

### 1.1 Synchronize Contraction Expansion & Apostrophe-Safe Quote Handling Across Both Document Halves
* **Severity**: 🟡 Major
* **Affected Scope**:
  - Feature Specification: [CUJ 2](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L62), [Mermaid Flowchart](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L87), and [Technical Plan Sections 1–3](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L93-L107)
  - Detailed Implementation Plan: [1. `engine/review/anti_ai_patterns.py`](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L163-L170), [2. `engine/review/humanization.py`](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L171-L183), and [6. `portal/feedback_editor.py`](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L218)
* **Simplicity Rationale**:
  - Consolidating contraction expansion directly into [`scrub_ai_tells()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L96-L136) (while URLs and double/single-quoted student spans are masked by [`_mask_protected_spans()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L66-L86)) eliminates the need for `_normalize_prose()` and cross-module private imports (`_expand`, `_outside_quotes`) in [`portal/feedback_editor.py`](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py).
  - Running `candidate = scrub_ai_tells(candidate, seed=nonce)` immediately after restoring `HZ<nonce>X<idx>Z` placeholders in [`validate_rewrite()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L99-L107) (before `_outside_quotes()`, `numeric()`, `quotes()`, qualifier checks, and the `6..95` word-count check) ensures that if `scrub_ai_tells()` strips a trailing `-ing` clause, the post-scrubbed candidate is still validated against every fact, number, quote, qualifier, and length guard.
  - Sharing the apostrophe-safe single-quote pattern between [`anti_ai_patterns.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L14) and [`humanization.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L18-L23) (`FACTS`, `_outside_quotes`, and `quotes`) prevents quote-boundary drift between the two offline modules without adding any new module or abstraction.

### 1.2 Synchronize Numbered-First Bulk Paste Rule (No Fallback When Numbered Markers Are Present) Across Both Halves
* **Severity**: 🟡 Major
* **Affected Scope**:
  - Feature Specification: [Technical Plan 4. Studio Client-Side Bulk Paste](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L108-L112)
  - Detailed Implementation Plan: [7. `portal/static/feedback-editor.js`](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L219-L235) and [10. `tests/test_feedback_editor_js.py`](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L259)
* **Simplicity Rationale**:
  - Returning the $K$ numbered blocks directly whenever $\ge 2$ sequential `1..K` line-start markers are present (so the caller's `blocks.length !== inputs.length` guard catches any merged or dropped comment) is simpler than conditional fallback and eliminates the multi-paragraph anchor-shift edge case.

---

## 2. Minor Alignment Nits

### 2.1 Remove Unused `bulkCommentsToggle` Reference in Detailed Implementation Plan Section 7
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L229)

### 2.2 Incorporate Stage 7 Wording & NFR Clarifications
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L13-L19) and [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L141-L147)
