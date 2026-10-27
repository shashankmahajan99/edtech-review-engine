# Deterministic ThinkingStorm v2 Anti-AI Scrubber, Stylometric Cadence & Voice Profile Upgrade

* **Author:** Shashank / ThinkingStorm Review Engine Team
* **Date:** 2026-10-27
* **Status:** Approved

## Overview

The ThinkingStorm v2 review pipeline (`engine/review/`) generates margin comments and a closing endnote letter inside native Word `.docx` deliverables. While the pipeline already includes initial banned-phrase checks and template selection, multi-comment deliverables can still exhibit uniform sentence lengths, repeated opener structures, repeated 5-grams across rules, symmetrical closing-letter paragraphs, and structural AI tells (such as copula avoidance, negative parallelisms, false ranges, and trailing participial riders).

This feature upgrades the offline deterministic review pipeline across six coordinated touchpoints without introducing any runtime model calls or breaking pinned humanizer contracts:
1. A 26-pattern structural AI-tell scrubber and auditor in `engine/review/anti_ai_patterns.py` that masks quoted student text and `https://knowledge.thinkingstorm.com/` URLs first, enforces the 0% contraction corpus standard by default, and supports opt-in deterministic seeded contraction modes.
2. Dynamic stylometric quantiles (`p10`, `p25`, `p50`, `p75`, `p90`), target coefficient of variation (`target_cv`), and 6 opener archetype distributions computed in `tools/mine_voice_corpus.py` and stored in `style_corpus/voice_profile.json`.
3. Stateful cross-comment cadence oscillation in `engine/review/persona.py` (`CommentComposer`) that alternates short/medium/expanded length bands, rotates opener archetypes, and applies deterministic non-greedy synonym slot perturbation seeded via `sha1(document_fingerprint | rule | position)`.
4. Asymmetric, bursty priority blocks in `engine/review/endnote.py` and `engine/review/endnote_moves.py` that vary paragraph rhythm across 1–3 focus areas while staying strictly within the `60/90/120` word minimums and the `138–382` word envelope.
5. Read-only coefficient of variation (`CV = std / mean >= 0.42`) and 5-gram repetition checks in `engine/review/style_guard.py`, `engine/review/validate.py`, and `engine/review/cli.py`, backed by a pre-write deterministic cadence pass so no valid deliverable is aborted at the XML release gate.
6. Documentation of local reviewer and humanizer prompt/sampling contracts in `LOCAL_THINKINGSTORM_REVIEWER.md` and `FEEDBACK_HUMANIZER.md` without altering pinned prompt hashes (`cc51d66b4c593fbe`) or sampling assertions in `tests/test_feedback_humanizer.py`.

## Analysis

### 1. Contrarian / YAGNI & Codebase Reuse (`egm-zoom-out`)
* **[Blocker] Four-Way Duplication of Banned Phrases and Contraction Maps**: `engine/review/anti_ai_patterns.py`, `engine/review/persona.py`, `engine/review/humanization.py`, and `engine/anti_ai_humanizer.py` each maintain separate regexes and lists for banned phrases, quote masking, and contractions. Instead of proliferating parallel lists, `engine/review/anti_ai_patterns.py` must serve as the single canonical source of truth for the 26 structural patterns and contraction tables, imported by `persona.py`, `style_guard.py`, `endnote.py`, and `validate.py`.
* **[Major] Hardcoded vs. Computed Quantiles in `tools/mine_voice_corpus.py`**: Lines 188–203 of `tools/mine_voice_corpus.py` currently hardcode `"sentence_length_quantiles"` and `"opener_archetypes"` instead of computing empirical quantiles and archetype rates from the mined corpus while falling back to the reference defaults when re-mining. `mine_voice_corpus.py` should compute actual percentiles from `all_sentences` and classify corpus comments using `classify_opener_archetype`.

### 2. System Architecture, Scaling & Envelopes (`egm-design`)
* **[Blocker] Endnote Word-Count Envelope vs. Asymmetric Priority Plans**: `validate.py:282` enforces minimum word counts `{1: 60, 2: 90, 3: 120}` by domain count, while `humanization.py:250` and `local_model.py:533` enforce `138 <= word_count <= 382`. If `endnote.py` selects three expanded priority plans plus follow-through text, the letter can breach 382 words; conversely, if it selects three terse plans (or 1 domain), it can drop below 138 words (or 60 words). `compose_endnote` must assign asymmetric roles across the ranked domains (Rank 0: deep anchored plan ~65–95 words; Rank 1: medium analytical plan ~40–60 words; Rank 2: compact directive plan ~28–42 words) and deterministically expand or trim follow-through sentences to stay inside `[max(minimum_words, 138), 382]` when 2–3 domains are present (and `[60, 382]` for single-domain edge cases).
* **[Major] Short-Review Variance Noise**: On manuscripts with only 1–3 comments, sentence-length `CV = std / mean` is statistically noisy and can fall below `0.42` even when comments are well-written. `style_guard.py` and `cli.py` must gate the `CV >= 0.42` enforcement on `len(bodies) >= 4` (with `len(sentences) >= 5`), matching the existing small-sample scaling in `style_guard.py:100`.

### 3. UX & Developer Ergonomics (`egm-comprehension`)
* **[Major] Actionable CLI Audit Output (`engine/review/cli.py`)**: When `python -m engine.review.cli audit <file.docx>` fails on `cv < 0.42`, `std < 2.6`, `repeated_ngram_ratio > 0.12`, or `audit_ai_tells`, the CLI output should name the specific tell identifiers, the actual vs. required CV (`cv >= 0.42`), and the repeated 5-gram ratio so an engineer can immediately see which check triggered `REVIEW`.
* **[Major] Missing Documentation Files (`LOCAL_THINKINGSTORM_REVIEWER.md` and `FEEDBACK_HUMANIZER.md`)**: Both files are referenced in developer workflows but do not currently exist in the repository. They must clearly document runtime environment variables (`TS_REVIEW_BACKEND`, `TS_HUMANIZER`, `TS_LOCAL_CONFIG`, `TS_HUMANIZER_CONFIG`), the offline rules guarantee, the 26-pattern anti-AI contract, and the pinned completion/instruct sampling parameters.

### 4. Migration, Backward Compatibility & Rollout Safety (`egm-implementation-readiness`)
* **[Blocker] Pinned `tests/test_feedback_humanizer.py` Contracts**:
  * `test_raw_prompt_and_sampling_match_upstream` asserts `sha256(h.prompt('X')).hexdigest()[:16] == 'cc51d66b4c593fbe'` and exact completion payload `{temperature: 1.0, top_p: 0.95, top_k: 0, min_p: 0, repeat_penalty: 1.0}`.
  * `test_instruct_editor_disables_reasoning_and_keeps_prose_contract` asserts `temperature=0.72, top_p=0.92` on pass 1 and `temperature=0.35, top_p=0.90` on retry.
  * `test_no_contractions_are_added_to_prose_or_expanded_inside_quotes` and `test_precise_date_correction_never_swaps_current_and_suggested_values` require that default `scrub_ai_tells(text, seed=...)` expands contractions outside quotes (`contraction_mode="expand"` default) and never alters `mla_date_numeric` / `apa_date_numeric` literal date strings or quoted spans.
* **[Blocker] Pre-Write Cadence Pass Ordering in `persona.py` / `pipeline.py`**: Because `validate_deliverable` checks that the XML comment bodies in `word/comments.xml` match `comment_bodies` byte-for-byte (`validate.py:184`) and that no comment sentence of 8+ words is copied verbatim into the endnote (`coverage.py` / `humanization.py:254`), the pre-write cadence pass must execute inside `compose_all()` in `engine/review/persona.py` (before `compose_endnote` and `humanize_review`).

### 5. Observability & Operational Debuggability (`egm-codebase-details`)
* **[Major] Complete 26-Pattern Taxonomy & Tell Reporting**: `engine/review/anti_ai_patterns.py` currently has 24 entries in `_BANNED_DISCOURSE` plus `_STAGED_RUNUPS` and Pattern 15 (`shallow_ing_riders`), but Pattern 1 (`not_only_but_also`) is scrubbed in `scrub_ai_tells` (line 158) without being checked in `audit_ai_tells`! Every single pattern in the 26-pattern table must be both scrubbed in `scrub_ai_tells()` and audited with a named tell ID in `audit_ai_tells()`, and exposed in `ValidationReport.metrics["style"]`.
* **[Nit] Quote & URL Masking Completeness**: `_mask_protected_spans` in `anti_ai_patterns.py` must mask `https://knowledge.thinkingstorm.com/\S+` and `https?://\S+`, `[[KEEP_...]]` markers, `HZ...X...Z` humanizer nonces, curly double/single quotes (`“...”`, `‘...’`), and straight double/single quotes while ignoring mid-word apostrophes (`don't`, `student's`) so contractions outside quotes are still caught.

### 6. Long-Term Tech Debt & Maintainability (`egm-structural`)
* **[Major] Stateful Cadence Oscillation Without Fragile Grammar Mutation**: Perturbing arbitrary words across templates risks breaking subject-verb agreement or changing pedagogical advice (which `humanization.py` rejects). Non-greedy synonym slot perturbation in `persona.py` must operate only on a curated, grammar-safe phrase-level alternation table (outside quotes and protected slots) and rely primarily on selecting among short (`<18` words), medium (`18–32` words), and expanded (`>32` words) template variants plus optional rule/category `EXTRAS` sentences when `compose_all` detects low sentence-length variance (`CV < 0.42`) or repeated 5-grams across the document's comment set.

## Goals vs. Non-Goals

* **In-Scope Goals:**
  * Implement and verify all 26 named anti-AI structural and lexical patterns in `engine/review/anti_ai_patterns.py` (`scrub_ai_tells` and `audit_ai_tells`), strictly masking quoted student text and `https://knowledge.thinkingstorm.com/` URLs, defaulting to 0% contractions (`contraction_mode="expand"`) while supporting deterministic seeded contraction modes (`contraction_mode="seeded"`).
  * Upgrade `tools/mine_voice_corpus.py` and `style_corpus/voice_profile.json` with empirical and reference sentence-length quantiles (`p10`–`p90`), `target_cv`, and 6 opener archetype distributions.
  * Upgrade `engine/review/persona.py` (`CommentComposer` and `compose_all`) with target length-band oscillation (`short` / `medium` / `expanded`), opener archetype alternation across the 6 archetypes, deterministic `sha1(document_fingerprint | rule | position)` non-greedy slot perturbation, and a pre-write cadence pass that guarantees cross-comment burstiness (`CV >= 0.42` when `>= 4` comments) and zero repeated 5-grams on regression fixtures.
  * Upgrade `engine/review/endnote.py` and `engine/review/endnote_moves.py` to compose asymmetric, bursty priority blocks within the `138–382` word envelope and `60/90/120` domain minimums.
  * Add read-only `CV >= 0.42` and 5-gram repetition metrics/checks to `engine/review/style_guard.py`, `engine/review/validate.py`, and `engine/review/cli.py`.
  * Write `LOCAL_THINKINGSTORM_REVIEWER.md` and `FEEDBACK_HUMANIZER.md` documenting local reviewer and humanizer anti-AI prompts, sampling parameters, and guardrails.
  * Add unit tests covering all 26 patterns, quote/URL masking, contraction modes, cadence oscillation, endnote asymmetry, and CLI audit checks while keeping all existing unittest and pytest suites green.

* **Out-of-Scope Non-Goals:**
  * Adding any LLM, network, or external detector calls to `engine/review/`.
  * Modifying `vendor/humanizer/prompt_format.json`, `PROMPT_FINGERPRINT` (`cc51d66b4c593fbe`), or `LocalHumanizer` transport sampling parameters in `engine/feedback_humanizer.py`.
  * Regenerating binary `.docx` test fixtures or modifying student manuscript text in `word/document.xml`.

## Key Decisions & Staging for Next Steps

1. **Contraction Policy**: Keep `contraction_mode: str = "expand"` as the default in `scrub_ai_tells(text, seed=0, contraction_mode="expand")` so the review pipeline and `test_feedback_humanizer.py` preserve the 0% contraction corpus standard, while supporting `contraction_mode="seeded"` for deterministic contraction injection outside quotes when explicitly requested.
2. **Pre-Write Cadence Pass vs. Read-Only Release Gate**: Perform all comment length-band selection, opener archetype rotation, and 5-gram deduplication inside `persona.py:compose_all()` before `compose_endnote()` and `write_deliverable()`. Keep `validate.py` strictly read-only, recording `cv` and `ngram_repeat` in `ValidationReport.metrics["style"]` (emitting a warning if `cv < 0.42` on `>= 4` comments, and failing hard only on banned/AI tells or structural Word defects), while `cli.py:cmd_audit` enforces `cv >= 0.42` and `repeated_ngram_ratio <= 0.12`.
3. **Asymmetric Endnote Budgeting**: In `endnote.py`, structure multi-domain closing letters with asymmetric domain lengths (primary priority expanded with concrete follow-through, secondary priority medium, tertiary priority concise) and enforce word-count clamping within `[max(minimum_words, 138), 382]` before scrubbing AI tells.
