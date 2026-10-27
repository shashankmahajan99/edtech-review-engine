# Stage 7: Critic Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target File**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L1-L158) (`FeatureRange: 1..158`)
**Reviewers**: Design Critic (`egm-design`), Structural Validator (`egm-structural`), Style Critic (`egm-style`)
**Summary**: **0 Blockers (🔴), 2 Majors (🟡), 3 Nits (🟢)**.

---

## 1. Design Critic Findings (`egm-design`)

### 1.1 Multi-Stage Bulk Paste Fallback Can Split Multi-Paragraph Numbered Comments and Shift Anchors
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L59-L61), [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L110-L111), and [feedback-editor.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/feedback-editor.js#L1-L133)
* **Finding**: Section 4 of the Technical Plan specifies that `FeedbackEditor.splitCommentBlock()` splits by sequential `1..N` markers first, then by blank lines, and finally by single lines. If a reviewer pastes a numbered block where Clever AI Humanizer merged or dropped a comment ($K = N - 1$ markers `[1]..[N-1]`) **and** one of those numbered comments contains an internal blank line, falling back from Stage 1 ($K \ne N$) to Stage 2 (blank-line splitting) will split the two-paragraph comment into two entries, producing $M == N$ blocks and shifting subsequent comments onto the wrong student quotes.
* **Recommendation**: Specify in Section 4 (and Detailed Implementation Section 7) that if the pasted text contains explicit leading numbering markers ($\ge 2$ lines starting with `[k]`, `k.`, `k)`, or `Comment k:`), `splitCommentBlock()` partitions by those markers (if sequential `1..K`) and returns the $K$ blocks directly **without** falling back to unnumbered blank-line or single-line splitting. That way, any missing or merged numbered comment fails the $M == N$ count gate deterministically.

### 1.2 Ordering of `scrub_ai_tells()` Inside `validate_rewrite()` and Apostrophe-Safe Quote Protection Across Modules
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L50), [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L95-L106), and [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L99-L146)
* **Finding**:
  1. In [`anti_ai_patterns.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L118-L124), `scrub_ai_tells()` strips trailing `-ing` clauses. Running `scrub_ai_tells()` at the end of `validate_rewrite()` (after `numeric()`, `quotes()`, `NEGATIONS`, and `6..95` word-count checks) could strip a protected number, quote, or negation token in that rider or shorten the comment below 6 words.
  2. Single-quoted student excerpts containing internal apostrophes (`‘don’t’`, `‘today’s’`) must be protected identically across `anti_ai_patterns.py`, `humanization.py`, and `portal/feedback_editor.py`.
* **Recommendation**:
  1. Specify that `validate_rewrite()` applies `scrub_ai_tells()` immediately after restoring `HZ<nonce>X<idx>Z` placeholders and **before** running `_outside_quotes()`, fact/number/quote counters, qualifier guards, and word-count bounds.
  2. Consolidate contraction expansion inside `scrub_ai_tells()` (after quote/URL masking) and reuse the apostrophe-safe single-quote pattern in `humanization.py`.

### 1.3 Document Post-Paste Server Validation Rejection & Case Preservation in `Non-Functional Requirements`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L141-L147)
* **Finding**: Document how the UI behaves if $M == N$ bulk paste succeeds on the client and triggers `POST /api/thinkingstorm/feedback/{job_id}`, but the server returns HTTP 422 on one comment (the pasted draft stays in `#commentEdit0..N-1` with dirty state active, download blocked, `#bulkCommentsInput` preserved, and the offending field linked in `#feedbackSaveErrors`), and note sentence-initial capitalization preservation in `scrub_ai_tells()`.

---

## 2. Structural Validator Findings (`egm-structural`)
* **Summary**: **0 Blockers (🔴), 0 Majors (🟡), 0 Nits (🟢)**. All mandatory headers, metadata fields, `Given`/`When`/`Then` CUJ blocks, Mermaid flowchart syntax, `Pros`/`Cons`/`Reason for Rejection` blocks, and relative Markdown links in `1..158` conform to the Feature Specification Standard.

---

## 3. Style Critic Findings (`egm-style`, `FeatureRange: 1..158`)

### 3.1 Precise Framing for External AI Detectors in `Overview`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L11-L13)
* **Style Rationale**: Prefer "eliminates deterministic AI-tell patterns and increases local sampling diversity" over "eliminates AI-detector triggers," as external black-box detectors are outside repository control.

### 3.2 Accurate Qualifier Token Count in `The Problem`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L19)
* **Style Rationale**: The parenthetical list `(not, no, never, without, cannot, may, might, could, likely, possibly, if, unless)` contains 12 tokens across negation, modal, and conditional categories; update "11 modal and conditional qualifier words" to "12 negation, modal, and conditional qualifier words."
