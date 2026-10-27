# Consolidated Goldfish Review Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target Specification**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md) (`FeatureRange: 1..158`, `DetailedRange: 159..279`)
**Execution Mode**: Preset 1 (`Consolidated report with all review rubrics` — Uninterrupted Full Flow)

## Executive Summary & Stage Reports

- **Summary**: **2 Blockers (🔴), 4 Majors (🟡), 5 Nits (🟢)** (deduplicated across all 5 review stages and 8 Goldfish reviewers).
- **Stage Reports**:
  - **Stage 5 (Initial Zoom Out)**: [zoom_out_report.md](file:///C:/Users/shashank/edtech-review-engine/zoom_out_report.md)
  - **Stage 6 (Comprehension Test)**: [comprehension_report.md](file:///C:/Users/shashank/edtech-review-engine/comprehension_report.md)
  - **Stage 7 (Critic Swarm: Design, Structural, Style)**: [critic_report.md](file:///C:/Users/shashank/edtech-review-engine/critic_report.md)
  - **Stage 8 (Intermediate Zoom Out)**: [intermediate_zoom_out_report.md](file:///C:/Users/shashank/edtech-review-engine/intermediate_zoom_out_report.md)
  - **Stage 9 (Implementation Readiness Swarm: Readiness, Codebase Details, Style)**: [implementation_readiness_report.md](file:///C:/Users/shashank/edtech-review-engine/implementation_readiness_report.md)

---

## 🔴 Blocker Findings

### B1. Uncaught Null-Reference Crash on `$('cleverOrigin')` in `portal/static/studio.js` Prevents `FeedbackEditor.mount()`
* **Source Stages**: Stage 9 (`egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L236-L242), [studio.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.js#L437-L465), [studio.html](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.html#L88-L106)
* **Description & Actionable Fix**:
  - In [studio.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.js#L437), `$('cleverOrigin').textContent = window.location.origin;` runs unconditionally immediately before `feedbackEditor = window.FeedbackEditor.mount(...)` (line 443) and `window.CleverWidget.mountDetector({document})` (line 465). Because `#cleverOrigin` is not in [studio.html](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.html), line 437 throws `TypeError: Cannot set properties of null (setting 'textContent')` in the browser and aborts script initialization before `FeedbackEditor.mount()` executes.
  - **Fix**: Update Detailed Implementation Plan Section 8 (`portal/static/studio.js`) to guard line 437 (`if ($('cleverOrigin')) $('cleverOrigin').textContent = window.location.origin;`).

### B2. Consolidate Quote-Preserving Contraction Expansion into `scrub_ai_tells()`, Align Single-Quote Regexes across `humanization.py` & `style_guard.py`, and Add `"Also"` / `"Note"` to `STARTERS`
* **Source Stages**: Stage 5 (`egm-zoom-out`), Stage 6 (`egm-comprehension`), Stage 7 (`egm-design`), Stage 8 (`egm-zoom-out`), Stage 9 (`egm-implementation-readiness`, `egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L93-L107), [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L163-L183), [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L217), [anti_ai_patterns.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L66-L136), [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L16-L146), [style_guard.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/style_guard.py#L75-L83), [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L211-L232)
* **Description & Actionable Fix**:
  1. **Quote-Safe Contraction Expansion Inside `scrub_ai_tells()`**: [`_outside_quotes()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L73) in `humanization.py` deletes quoted substrings (`re.sub(..., '', text)`) rather than masking and restoring them, whereas [`scrub_ai_tells()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L96-L136) in `anti_ai_patterns.py` already masks URLs, double quotes, and apostrophe-safe single quotes via [`_mask_protected_spans()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L66-L86). Replace the old contraction-injection pass in `scrub_ai_tells()` with quote-protected contraction expansion (`_CONTRACTIONS` regex table expanding `don't` -> `do not`, `it's` -> `it is`, etc., preserving leading capitalization on `masked` before `_unmask_protected_spans()`). This makes `scrub_ai_tells()` the single canonical 0%-contraction and anti-AI normalizer across offline generation, `humanization.py`, and `portal/feedback_editor.py`.
  2. **Single-Quote Regex Alignment**: Update [`humanization.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L19) (`FACTS`, `_outside_quotes`, and `quotes`) and [`banned_hits()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/style_guard.py#L79-L80) in `style_guard.py` to use the same apostrophe-safe single-quote patterns (`‘(?:[^’]|(?<=\w)’(?=\w))*’` and `(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w))*'(?!\w)`) as `anti_ai_patterns.py`.
  3. **`STARTERS` & Ordering in `validate_rewrite()`**: Run `candidate = scrub_ai_tells(candidate, seed=nonce)` immediately after restoring `HZ<nonce>X<idx>Z` placeholders in [`validate_rewrite()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L99-L107) (before `_outside_quotes()`, fact/number/quote counters, qualifier guards, `new_names`, and the `6..95` word-count check) and add `"Also"` and `"Note"` to [`STARTERS`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L16) so sentence-initial replacements (`"Also, "`, `"Note that "`) are not rejected as new named terms.

---

## 🟡 Major Findings

### M1. Prevent Stage 1 Numbered Bulk-Paste Blocks from Falling Through to Unnumbered Splitting & Specify Exact Regexes and Async Save Handling in `portal/static/feedback-editor.js`
* **Source Stages**: Stage 7 (`egm-design`), Stage 8 (`egm-zoom-out`), Stage 9 (`egm-implementation-readiness`, `egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L110-L111), [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L219-L235), [feedback-editor.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/feedback-editor.js#L62-L132)
* **Description & Actionable Fix**:
  - **Stage 1 No-Fallthrough Rule & Exact Regexes**: If a reviewer pastes a numbered block where Clever AI Humanizer merged or dropped a comment ($K \ne N$ markers `1..K` with $K \ge 2$) and one comment wraps or contains a blank line, falling back to Stage 2/3 can split that comment into two blocks and falsely pass $M == N$. Specify that Stage 1 matches line-start markers `^\s*(?:\[(\d+)\]|Comment\s+(\d+)\s*[:.)]|(\d+)[.)])\s+` and, whenever $\ge 2$ lines match sequential `1..K` markers, returns those $K$ blocks directly without falling back to Stages 2–3. In Stages 2–3, only strip a leading marker if all blocks carry sequential `1..M` markers (or a single block starts with `[1]` / `Comment 1:`), ensuring dates like `20 Feb. 2026` are never stripped.
  - **Async Save & Disabled State**: Specify that `refresh()` sets `disabled = saving || !data?.editing_available` on `bulkCommentsInput` and `applyBulkCommentsBtn`, and that the `applyBulkCommentsBtn` click listener is `async` and `await`s `$('saveFeedbackBtn')?.click()`. Remove the unused `bulkCommentsToggle` ID from Section 7.

### M2. Forward `retry=retry` Inside `LocalHumanizer.__call__` Session Wrapper & Specify `inspect.signature` Check in `humanize_review()`
* **Source Stages**: Stage 9 (`egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L181-L191), [feedback_humanizer.py](file:///C:/Users/shashank/edtech-review-engine/engine/feedback_humanizer.py#L118-L129), [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L190-L194)
* **Description & Actionable Fix**:
  - Update line 121 of [`engine/feedback_humanizer.py`](file:///C:/Users/shashank/edtech-review-engine/engine/feedback_humanizer.py#L118-L121) (`if not self._active: with self.session(): return self(text, retry=retry)`) so direct calls outside `with humanizer.session():` forward `retry=retry`.
  - Specify in Section 2 (`engine/review/humanization.py`) that `humanize_review()` inspects `'retry' in inspect.signature(rewrite).parameters` once before the loop and calls `rewrite(masked, retry=attempt > 0)` when supported, falling back to `rewrite(masked)` for 1-argument test callables.

### M3. Specify Exact Endnote Narrative Paragraph Predicate & `_save_issues()` Error Formatting in `portal/feedback_editor.py`
* **Source Stages**: Stage 5 (`egm-zoom-out`), Stage 9 (`egm-implementation-readiness`, `egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L217), [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L59-L88) & [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L211-L232)
* **Description & Actionable Fix**:
  - Import [`is_endnote_heading`](file:///C:/Users/shashank/edtech-review-engine/engine/review/letter_format.py#L17-L25) from `engine.review.letter_format` in `portal/feedback_editor.py`. When normalizing `letter` in `save_feedback()`, skip index `0` when `p.startswith('Dear ')`, skip any heading where `is_endnote_heading(p)` is true, and skip any closing sign-off/signature paragraph where `state['reviewer'].lower() in p.lower()` or `re.match(r'^(?:All the best|Best wishes|Best regards|Warm regards|Sincerely|Thanks|Thank you)\b', p, re.I)`.
  - In `_save_issues()`, compute `hits = list(dict.fromkeys(banned_hits(text) + audit_ai_tells(text)))` in both the comment and endnote `'banned'` branches so endnotes failing `audit_ai_tells()` display the exact offending tells rather than `[]`.

### M4. Partition Detailed Implementation Plan into Incremental Phases & Checkpoints
* **Source Stages**: Stage 9 (`egm-implementation-readiness`, `egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L159-L273)
* **Description & Actionable Fix**:
  - Organize the Detailed Implementation Plan into 3 incremental phases with verification checkpoints per [implementation-readiness-standard.md](file:///C:/Users/shashank/edtech-review-engine/vendor/elephant-goldfish-model/resources/document_standards/implementation-readiness-standard.md#L20-L23):
    - **Phase 1: Offline Scrubber, Guarded Humanizer & Release Gate** (`anti_ai_patterns.py`, `style_guard.py`, `humanization.py`, `feedback_humanizer.py`, `editor_prompt.txt`, `validate.py`)
    - **Phase 2: Portal Save Normalization & Field-Level Issue Mapping** (`portal/feedback_editor.py`)
    - **Phase 3: Studio Bulk Paste UI & Verification Suite** (`portal/static/feedback-editor.js`, `portal/static/studio.js`, `portal/static/studio.html`, `portal/static/workspace.css`, `tests/`)

---

## 🟢 Nit Findings

### N1. Clarify `ADVICE_START` Origin & Shared `RejectedRewrite` Exception Message in Section 2
* **Source Stages**: Stage 6 (`egm-comprehension`), Stage 9 (`egm-implementation-readiness`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L177-L179)
* **Description & Actionable Fix**: Note that `ADVICE_START` is an existing constant in `engine/review/humanization.py` (lines 46–49) and that `NEGATIONS`, `STRICT_CONDITIONALS`, and `UNCERTAINTY` mismatches all raise `RejectedRewrite('negation, conditions or uncertainty changed')`.

### N2. Use Exact Symbol Name `_CONTRACTIONS_MAP` and Step `# 5.` in Section 1
* **Source Stages**: Stage 9 (`egm-implementation-readiness`, `egm-codebase-details`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L168)
* **Description & Actionable Fix**: Replace `_CONTRACTION_INJECTIONS` / "step 6" with `_CONTRACTIONS_MAP` (line 52) / step `# 5. Deterministic Contraction Injection` (line 126) and remove unused `import hashlib`.

### N3. Document Post-Paste HTTP 422 Recovery & Sentence-Initial Capitalization in `Non-Functional Requirements`
* **Source Stages**: Stage 7 (`egm-design`), Stage 8 (`egm-zoom-out`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L141-L147)
* **Description & Actionable Fix**: Note in `Non-Functional Requirements` that if $M == N$ bulk paste triggers `POST /api/thinkingstorm/feedback/{job_id}` and the server returns HTTP 422 on one comment, the pasted draft stays in `#commentEdit0..N-1` with dirty state active, download blocked, `#bulkCommentsInput` preserved, and the offending field linked in `#feedbackSaveErrors`. Also note that `scrub_ai_tells()` preserves sentence-initial capitalization on replacements.

### N4. Precise Framing for External AI Detectors and Qualifier Token Count in `Overview` & `The Problem`
* **Source Stages**: Stage 7 (`egm-style`), Stage 8 (`egm-zoom-out`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L13-L19)
* **Description & Actionable Fix**: Update line 13 to "eliminates deterministic AI-tell patterns and increases local sampling diversity" and line 19 to "all 12 negation, modal, and conditional qualifier words."

### N5. Trim Minor Filler Phrasing in Section 9 (`portal/static/studio.html`)
* **Source Stages**: Stage 9 (`egm-style`)
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L248-L250)
* **Description & Actionable Fix**: Replace "so it accurately describes" and "with accessible labels and accurate user guidance" with direct factual phrasing.

---

## Traceability Matrix

| Consolidated ID | Severity | Stage 5: Initial Zoom Out | Stage 6: Comprehension Test | Stage 7: Critic Swarm | Stage 8: Intermediate Zoom Out | Stage 9: Implementation Readiness Swarm |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **B1** (`$('cleverOrigin')` null guard in `studio.js`) | 🔴 Blocker | — | — | — | — | `implementation_readiness_report.md` #1 |
| **B2** (`scrub_ai_tells()` contraction expansion, single-quote regexes, `STARTERS`) | 🔴 Blocker | `zoom_out_report.md` #1, #2 | `comprehension_report.md` #2 | `critic_report.md` #1.2 | `intermediate_zoom_out_report.md` #1.1 | `implementation_readiness_report.md` #2 |
| **M1** (Stage 1 numbered no-fallthrough, exact regexes, async save & disabled state) | 🟡 Major | `zoom_out_report.md` #3 | `comprehension_report.md` #3 | `critic_report.md` #1.1 | `intermediate_zoom_out_report.md` #1.2, #2.1 | `implementation_readiness_report.md` #4 |
| **M2** (`LocalHumanizer.__call__` `retry` forwarding & `inspect.signature`) | 🟡 Major | — | — | — | — | `implementation_readiness_report.md` #3 |
| **M3** (Endnote narrative paragraph predicate & `_save_issues()` hits) | 🟡 Major | `zoom_out_report.md` #1 | — | — | `intermediate_zoom_out_report.md` #1.1 | `implementation_readiness_report.md` #5 |
| **M4** (Incremental implementation phases & checkpoints) | 🟡 Major | — | — | — | — | `implementation_readiness_report.md` #6 |
| **N1** (`ADVICE_START` origin & `RejectedRewrite` message) | 🟢 Nit | — | `comprehension_report.md` #1 | — | — | `implementation_readiness_report.md` #8 |
| **N2** (`_CONTRACTIONS_MAP` & step `# 5.` naming in `anti_ai_patterns.py`) | 🟢 Nit | — | — | — | — | `implementation_readiness_report.md` #7 |
| **N3** (Post-paste HTTP 422 recovery & capitalization preservation in NFRs) | 🟢 Nit | — | — | `critic_report.md` #1.3 | `intermediate_zoom_out_report.md` #2.2 | — |
| **N4** (Detector phrasing & 12 qualifier tokens in `Overview` / `The Problem`) | 🟢 Nit | — | — | `critic_report.md` #3.1, #3.2 | `intermediate_zoom_out_report.md` #2.2 | — |
| **N5** (Trim filler wording in Section 9 `studio.html`) | 🟢 Nit | — | — | — | — | `implementation_readiness_report.md` #9 |
