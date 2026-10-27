# Stage 9: Implementation Readiness Report (`docs/designs/anti-ai-humanization-and-bulk-paste.md`)

**Target File**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L159-L279) (`DetailedRange: 159..279`)
**Reviewers**: Implementation Readiness (`egm-implementation-readiness`), Codebase Details (`egm-codebase-details`), Style Critic (`egm-style`)
**Summary**: **2 Blockers (🔴), 4 Majors (🟡), 3 Nits (🟢)**.

---

## 🔴 Blockers

### 1. Uncaught Null-Reference Crash on `$('cleverOrigin')` in `portal/static/studio.js` Prevents `FeedbackEditor.mount()`
* **Severity**: 🔴 Blocker
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L236-L242), [studio.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.js#L437-L465), [studio.html](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.html#L88-L106)
* **Discrepancy Description & Rationale**: In [studio.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.js#L437), `$('cleverOrigin').textContent = window.location.origin;` runs unconditionally immediately before `feedbackEditor = window.FeedbackEditor.mount(...)` (line 443) and `window.CleverWidget.mountDetector({document})` (line 465). Because `#cleverOrigin` is not present in [studio.html](file:///C:/Users/shashank/edtech-review-engine/portal/static/studio.html), line 437 throws `TypeError: Cannot set properties of null (setting 'textContent')` in the browser and aborts script initialization before `FeedbackEditor.mount()` executes.
* **Required Fix**: Specify in Detailed Implementation Plan Section 8 (`portal/static/studio.js`) that line 437 must be guarded (`if ($('cleverOrigin')) $('cleverOrigin').textContent = window.location.origin;`).

### 2. Quote-Preserving Contraction Expansion, Single-Quote Regex Alignment, and `STARTERS` Ordering in `validate_rewrite()`
* **Severity**: 🔴 Blocker
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L163-L183) & [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L217), [anti_ai_patterns.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L66-L136), [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L16-L23) & [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L146), [style_guard.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/style_guard.py#L75-L83), [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L211-L232)
* **Discrepancy Description & Rationale**:
  1. **Quote Deletion in `_outside_quotes()`**: Section 6 instructs `portal/feedback_editor.py` to import `_outside_quotes` from `engine.review.humanization` to expand contractions outside quoted spans. However, [`_outside_quotes()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L72-L73) deletes quoted spans (`re.sub(..., '', text)`) rather than masking and restoring them. Instead, expand contractions directly inside [`scrub_ai_tells()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/anti_ai_patterns.py#L96-L136) while URLs, double quotes, and apostrophe-safe single quotes are already masked by `_mask_protected_spans()`.
  2. **Single-Quote Regex Alignment**: [`humanization.py`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L19) (`FACTS`, `_outside_quotes`, and `quotes`) still uses `‘[^’]*’` (which terminates at a word-internal apostrophe `’`), and [`banned_hits()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/style_guard.py#L79-L80) in `style_guard.py` only strips double quotes (`\u201c[^\u201d]*\u201d` and `"[^"]*"`), ignoring single-quoted student excerpts. Align `humanization.py` and `style_guard.py` to use the apostrophe-safe single-quote patterns (`‘(?:[^’]|(?<=\w)’(?=\w))*’` and `(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w))*'(?!\w)`).
  3. **`STARTERS` vs. `scrub_ai_tells()` in `validate_rewrite()`**: Running `candidate = scrub_ai_tells(candidate, seed=nonce)` immediately after restoring `HZ<nonce>X<idx>Z` placeholders in [`validate_rewrite()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L99-L107) can introduce sentence-initial `"Also, "` or `"Note that "`, which triggers `RejectedRewrite('new named term')` at line 134 unless `"Also"` and `"Note"` are added to [`STARTERS`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L16).

---

## 🟡 Majors

### 3. Forward `retry=retry` Inside `LocalHumanizer.__call__` Session Wrapper & Specify `inspect.signature` Check
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L181-L191), [feedback_humanizer.py](file:///C:/Users/shashank/edtech-review-engine/engine/feedback_humanizer.py#L118-L129), [humanization.py](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L190-L194)
* **Discrepancy Description & Rationale**:
  - In [`LocalHumanizer.__call__`](file:///C:/Users/shashank/edtech-review-engine/engine/feedback_humanizer.py#L118-L121), when `not self._active`, line 121 recursively calls `return self(text)`. It must be updated to `return self(text, retry=retry)` so direct calls outside an active `with humanizer.session():` block forward `retry=True`.
  - In [`humanize_review()`](file:///C:/Users/shashank/edtech-review-engine/engine/review/humanization.py#L190-L194), explicitly specify checking `'retry' in inspect.signature(rewrite).parameters` before calling `rewrite(masked, retry=attempt > 0)` (rather than catching `TypeError`, which could mask internal errors in test callables).

### 4. Exact Regexes, Stage 1 No-Fallthrough Rule, and Async/Disabled Wiring in `portal/static/feedback-editor.js`
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L219-L235), [feedback-editor.js](file:///C:/Users/shashank/edtech-review-engine/portal/static/feedback-editor.js#L62-L132)
* **Discrepancy Description & Rationale**:
  - **Stage 1 No-Fallthrough & Exact Regexes**: Specify the exact line-start marker regex (`^\s*(?:\[(\d+)\]|Comment\s+(\d+)\s*[:.)]|(\d+)[.)])\s+`) and requires that if $\ge 2$ lines match sequential `1..K` markers, `splitCommentBlock()` returns those $K$ blocks directly without falling through to Stages 2–3, and that Stages 2–3 only strip a leading marker when it matches `^\s*(?:\[1\]|Comment\s+1\s*[:.)]|1[.)])\s+` (or sequential `1..M`), preventing dates like `20 Feb. 2026` from being matched.
  - **Async Save & Disabled State**: Specify that `refresh()` sets `disabled = saving || !data?.editing_available` on `bulkCommentsInput` and `applyBulkCommentsBtn`, and that the `applyBulkCommentsBtn` click handler is `async` and `await`s `$('saveFeedbackBtn')?.click()`. Remove the unused `bulkCommentsToggle` ID from Section 7.

### 5. Endnote Narrative Paragraph Predicate & `_save_issues()` Error Formatting in `portal/feedback_editor.py`
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L209-L217), [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L59-L88) & [feedback_editor.py](file:///C:/Users/shashank/edtech-review-engine/portal/feedback_editor.py#L211-L232)
* **Discrepancy Description & Rationale**:
  - Specify the exact narrative-paragraph predicate for `letter` in `save_feedback()`: skip index `0` when it starts with `Dear `, skip any heading where `is_endnote_heading(p)` is true, and skip any closing sign-off/signature paragraph where `state['reviewer'].lower() in p.lower()` or `re.match(r'^(?:All the best|Best wishes|Best regards|Warm regards|Sincerely|Thanks|Thank you)\b', p, re.I)`.
  - Specify that `_save_issues()` uses `list(dict.fromkeys(banned_hits(text) + audit_ai_tells(text)))` when formatting both comment and endnote banned-phrasing messages so endnotes failing `audit_ai_tells()` never display `[]`.

### 6. Add Incremental Implementation Phases & Checkpoints
* **Severity**: 🟡 Major
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L159-L273)
* **Discrepancy Description & Rationale**: Partition the 10 implementation items into 3 incremental phases (`Phase 1: Offline Scrubber, Guarded Humanizer & Release Gate [Items 1–5]`, `Phase 2: Portal Save Normalization & Issue Mapping [Item 6]`, `Phase 3: Studio Bulk Paste UI & Verification Suite [Items 7–10]`) with per-phase test checkpoints per [implementation-readiness-standard.md](file:///C:/Users/shashank/edtech-review-engine/vendor/elephant-goldfish-model/resources/document_standards/implementation-readiness-standard.md#L20-L23).

---

## 🟢 Nits

### 7. Exact Constant/Comment Names in `engine/review/anti_ai_patterns.py`
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L168)
* **Discrepancy Description & Rationale**: Refer to `_CONTRACTIONS_MAP` (line 52) and step `# 5. Deterministic Contraction Injection` (line 126) in `engine/review/anti_ai_patterns.py`, and remove the unused `import hashlib`.

### 8. Clarify `ADVICE_START` Origin & Shared `RejectedRewrite` Message in Section 2
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L177-L179)
* **Discrepancy Description & Rationale**: Note that `ADVICE_START` is an existing regex constant in `engine/review/humanization.py` (lines 46–49) and that all three qualifier checks (`NEGATIONS`, `STRICT_CONDITIONALS`, `UNCERTAINTY`) raise `RejectedRewrite('negation, conditions or uncertainty changed')`.

### 9. Trim Minor Filler Phrasing in Section 9 (`portal/static/studio.html`)
* **Severity**: 🟢 Nit
* **Affected Scope**: [anti-ai-humanization-and-bulk-paste.md](file:///C:/Users/shashank/edtech-review-engine/docs/designs/anti-ai-humanization-and-bulk-paste.md#L248-L250)
* **Discrepancy Description & Rationale**: Replace "so it accurately describes" and "with accessible labels and accurate user guidance" with direct factual phrasing.
