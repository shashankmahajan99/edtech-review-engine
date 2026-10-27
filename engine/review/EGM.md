# engine/review: Deterministic Review Pipeline

## Overview

`engine/review/` is the repository's release-grade manuscript review engine. It
turns a `.docx` draft into a delivered review package: native Word margin
comments anchored to the exact quoted words, one knowledge-base hyperlink per
labelled comment, and a native endnote letter in `word/endnotes.xml`.

The package is deterministic and offline by default. The rules path
(`backend="rules"`) uses no model, no network and no token budget; parsing the
same file twice yields the same model and the same findings. The optional
`local` backend talks only to a loopback HTTP endpoint configured in
`output/local-model/config.json`; there is no cloud fallback.

A third, opt-in stage may edit the generated *feedback* (never the manuscript):
an injected `feedback_rewriter` is wrapped by `humanization.humanize_review`,
which masks facts and rejects any rewrite that loses a quotation, name, URL,
number, qualification or advice direction. The rewriter is supplied by the
caller; with `feedback_rewriter=None` the pipeline is byte-for-byte
deterministic and no model transport is imported or called. The offline guards
in `humanization.py` are always importable, but they run only when a rewriter is
injected.

The design premise is that the deliverable must never damage the student's
manuscript. Text nodes are only split, never rewritten, and
`validate.validate_deliverable` re-opens the produced package and inspects the
XML independently of the writer before anything ships.

Pipeline shape (`pipeline.review_document`):

```
input.docx -> load_document -> analyze -> select -> compose -> [humanize] -> coverage -> write/anchor -> validate -> deliver
```

## Problem & Scope

- `engine/review/` must turn a `.docx` manuscript into a delivered review package
  without damaging the student's text: native margin comments anchored to quoted
  words, one knowledge-base hyperlink per labelled comment, a native endnote letter,
  and a redline copy of the body.
- It is the release-gated path the portal calls; `validate.validate_deliverable`
  re-opens the produced package and fails closed before anything ships.
- Scope is a single `.docx` in and a `.docx` plus `.review.json` sidecar out. It has
  no server, queue or database; the watcher is a filesystem loop.
- The `rules` backend is the default and must stay deterministic and offline; the
  optional `local` backend talks only to a loopback model endpoint.
- An optional, injected feedback humanizer may rephrase the composed comments and
  letter before they are written. It is never part of the rules path: the caller
  passes `feedback_rewriter`, the transport lives outside the package
  (`engine.feedback_humanizer`) and `humanization.py` only guards what it returns.

## Goals & Non-Goals

- Goal: exact-span anchoring. Every delivered comment range covers the quoted words,
  whitespace-normalized, and a missing or duplicate anchor is a hard error.
- Goal: character-identical paragraph text. The writer only splits runs and the gate
  rejects any drift.
- Goal: deterministic output on the rules path, so the same draft yields the same
  model, findings, comments and ordering.
- Goal: guarded humanization. A rewrite may change wording only; protected facts,
  quotations, numbers, negation, advice direction, letter greeting, signature and
  comment anchors survive, and any rejected passage keeps its original prose.
- Non-goal: cloud model use. The `local` backend must resolve to a loopback HTTP host
  and a provider in `{ollama, strata, llamacpp}`; anything else raises
  `LocalReviewError`. The humanizer transport enforces the same loopback-only rule.
- Non-goal: rewriting the student's prose. Neither the pipeline nor the humanizer
  paraphrases the manuscript; the humanizer edits reviewer feedback and the letter.
- Non-goal: a general-purpose review service. There is no API server here; the CLI and
  watcher are the entry points.

## Alternatives Considered

- Rebuilding the DOCX from extracted text: rejected because it loses images, tables,
  fonts and styles; the writer copies the package entry-for-entry and edits only the
  XML parts it needs.
- A model-only reviewer as the default: rejected because determinism, the release gate
  and exact anchoring are the package's guarantees; the `local` backend remains opt-in.
- Anchoring comments by paragraph index instead of exact spans: rejected because Word
  comments must highlight the quoted words; `normalize_span` and `can_anchor` enforce
  the range and drop or abort unanchorable findings.
- A database-backed queue for the watcher: rejected because the watcher is a simple
  filesystem loop with `processed.json`, `done/` and `failed/`; a queue would add an
  operational dependency the package does not need.
- Unguarded rewriting: rejected because a model edit can silently drop a quotation,
  invert advice or invent a completed edit. `humanization.validate_rewrite` is the
  reason an edit may enter the deliverable at all; the alternative was to forbid
  rewriting entirely, which the reviewer workflow needs for register edits.
- Requiring the humanizer: rejected because the release gate and reproducibility must
  not depend on a local model process. It stays an injected, opt-in collaborator.

## Risks & Mitigations

- The release gate only enforces what its validators check; page coverage and density
  are warnings, not failures. Mitigation is reviewer QA plus `cli audit`.
- A rule that depends on the wall clock (`_CURRENT_YEAR`) can change findings at a
  year boundary or between processes started in different years. Mitigation is to
  document the clock input; freezing or deriving the cutoff is a code change.
- Word can silently repair a package with duplicate relationships or content after
  `w:sectPr`, dropping comments. Mitigation is `_native_package_problems`, which
  rejects those packages before delivery.
- The optional `local` backend sends the manuscript to a loopback model, so determinism
  and air-gap claims only hold for the rules backend. Mitigation is the explicit
  backend selector and `LocalReviewError` on any non-loopback host.
- Pre-existing comments are appended to rather than replaced; a second pass can overlap
  reviewer ranges. Mitigation is the `allow_existing_comments` gate and the documented
  "pre-existing ranges may overlap" carve-out.
- A humanizer can only damage what the guards do not measure. Mitigation is fact
  masking plus `validate_rewrite`, a rollback when the letter leaves its 138-382 word
  reference range or repeats a comment sentence, and a `needs_review` flag plus
  quality warning whenever any passage had to be retained.
- An injected rewriter that raises `HumanizerUnavailable` (or any `RuntimeError`/
  `ValueError`) aborts the run with `PipelineError` before a file is written, so a
  broken model process can never produce a half-edited deliverable.

## Interface

### Package surface (`__init__.py`)

- `__version__ = "2.0.0"`; the documented public surface is `review_document`
  (import from `engine.review.pipeline`; `__init__` does not re-export it) plus the
  CLI/watcher entry points. Submodules (`diagnostics`, `kb`, `ingest`, ...) are
  imported directly by the portal and tools.

### Pipeline (`pipeline.py`)

- `class PipelineError(RuntimeError)`: raised when a manuscript cannot be
  reviewed safely (unsupported file, existing comments without opt-in, too
  short, unanchorable comments, failed validation).
- `@dataclass ReviewResult`: `input_path`, `output_path`, `report_path`,
  `comments`, `endnote`, `analysis`, `validation`, `elapsed_seconds`, `model`,
  `quality`, `generation`.
- `review_document(input_path, output_dir=None, reviewer_name="Raunak Banga", reviewer_initials="RB", student_name=None, academic_style="auto", allow_existing_comments=False, overwrite=False, comprehensive=True, backend=None, local_checkpoint=None, feedback_rewriter=None, progress=None) -> ReviewResult`:
  the end-to-end entry point. `feedback_rewriter` is an optional callable
  (`text -> text`, optionally with a `session()` context manager and `model`/
  `model_name` attributes) wrapped by `humanization.humanize_review`; `progress`
  is an optional callable receiving stage dicts via `progress.emit_progress`.
- Backend selection: `backend` argument, else `TS_REVIEW_BACKEND`, else
  `"rules"`; an unknown value raises `PipelineError`. The CLI applies
  `engine.review_runtime.apply_runtime_defaults()` first, which is what makes a
  deployed profile select `local`/humanizer without changing this function.

### Document model (`docmodel.py`)

- `class TextNode`, `class Paragraph` (`index`, `element`, `text`, `nodes`,
  `style`, `in_table`, `region`, `is_heading`; properties `words`,
  `normalized`; method `slice_text`).
- `class DocumentModel` (`path`, `paragraphs`, `doc`, `fingerprint`, `style`,
  `has_existing_comments`, `meta`; properties `body_paragraphs`,
  `prose_paragraphs`, `front_matter`, `references`, `full_text`, `word_count`).
- `w(tag)`, `build_paragraph(element, index, in_table=False)`,
  `classify_regions(paragraphs)`, `reference_heading_span(text)`,
  `detect_existing_comments(path)`, `load_document(path, academic_style="auto")`,
  `detect_style(text, paragraphs)`, `strip_quotes(s)`.
- Region vocabulary: `front_matter`, `title`, `abstract`, `body`,
  `references`, `table`, `blank`, `reviewer_note`.

### Analysis (`analysis.py`)

- `@dataclass Finding`: `rule_id`, `category`, `paragraph`, `start`, `end`,
  `facts`, `priority` (0-100); properties `quote`, method `key()`.
- `@dataclass Block`: paragraph grouping used by the rules; `span_in_paragraph`,
  `sentences()`.
- `@dataclass AnalysisResult`: `findings`, `essay_type`, `sources`, `metrics`,
  `blocks`.
- `analyze(model) -> AnalysisResult`, plus the rule families
  `front_matter_rules`, `abstract_rules`, `thesis_rules`, `body_rules`,
  `conclusion_rules`, `counterargument_rules`, `mechanics_rules`,
  `reference_rules`, `statement_rules`.
- Category constants: `THESIS`, `INTRO`, `ORGANISATION`, `TOPIC`, `TRANSITION`,
  `EVIDENCE`, `STATISTICS`, `ANALYSIS`, `COUNTER`, `CONCLUSION`, `ABSTRACT`,
  `MLA`, `APA`, `PUNCT`, `FRAGMENTS`, `SVA`, `INFORMAL`, `CLARITY`.
- Span helpers: `trim_span`, `sentence_span`, `snippet_around`, `build_blocks`,
  `quoted_passages`.

### Selection (`selection.py`)

- `@dataclass SelectedComment`: `finding`, `category`, `labelled`.
- `select_comments(model, result, comprehensive=False) -> list[SelectedComment]`.
- Budget tables: `CATEGORY_CAPS`, `RULE_CAPS`, `MERGE_PAIRS`, `RHETORICAL`,
  `ALWAYS_LABELLED`.

### Composition (`persona.py`, `pedagogy.py`, `endnote.py`, `endnote_moves.py`, `kb.py`, `links.py`)

- `class CommentComposer` (`compose(selected)`, `scan_style(text)`),
  `compose_all(model, selected, essay_type) -> list[tuple[SelectedComment, str]]`.
- `class CompositionError(ValueError)`: a finding has no complete, rule-specific
  wording.
- `human_date(numeric, style)`, `BANNED_PHRASES`.
- `@dataclass Endnote`: `paragraphs`, `domains`, `word_count`, `evidence`;
  `compose_endnote(model, result, reviewer_name=..., student_name=..., composed=...)`.
- `endnote_moves.PRIORITY_PLANS`: rule id -> next-step prose template used by
  `compose_endnote` to build the student's action plan for that diagnosis; anchors
  are substitution values from the student's own text, not invented examples.
- `pedagogy.rhetoric(model, blocks)`, `pedagogy.mechanics(model, blocks)`,
  `pedagogy.formatting(model)`; `pedagogy.TEMPLATES`.
- `kb.load()`, `kb.banned_phrases()`, `kb.persona()`, `kb.anti_ai_rules()`,
  `kb.endnote_template()`, `kb.facts_for(model, finding)`,
  `kb.patterns_for_rule(rule, model, finding)`.
- `links.link_for(category, model=None)`, `links.is_allowed(url)`,
  `links.BASE = "https://knowledge.thinkingstorm.com"`.

### Writing (`writer.py`, `trackchanges.py`)

- `@dataclass WriteResult`: `path`, `comment_ids`.
- `write_deliverable(model, composed, endnote_paragraphs, output_path, reviewer_name="Raunak Banga", reviewer_initials="RB") -> WriteResult`.
- Anchoring: `explode_runs(paragraph_element)`,
  `normalize_span(paragraph_element, start, end)`,
  `can_anchor(paragraph_element, start, end)`,
  `anchor_comment(paragraph_element, start, end, cid)`.
- Package constants: `COMMENT_PART`, `COMMENT_RELS`, `ENDNOTE_PART`,
  `DOC_PART`, `DOC_RELS`, `CONTENT_TYPES`, `STYLES_PART`.
- `trackchanges.apply_line_edits(input_path, output_path, edits, author="Apex Admissions Editorial Desk") -> int`:
  native `<w:del>`/`<w:ins>` redline that copies the package entry-for-entry,
  edits only `word/document.xml`, and returns the number of edits applied.

### Guarded humanization (`humanization.py`)

- `class RejectedRewrite(ValueError)` and `class TruncatedRewrite(RejectedRewrite)`:
  a candidate violates a preservation rule, or the transport stopped at its token
  limit (a truncated candidate may be retried but is never delivered).
- `mask_facts(text, known_names=()) -> (masked, protected, nonce)`: replaces
  quotations, names, URLs, dates, numbers/units and `[[KEEP_*]]` markers with
  `HZ<nonce>X<n>Z` placeholders. Sentence-initial imperatives and ordinary
  capitalized nouns are deliberately *not* masked.
- `validate_rewrite(original, candidate, protected, nonce, *, developmental=False, comment=True) -> str`:
  restores the placeholders and rejects an empty candidate, a lost/duplicated/
  invented fact, changed quotations or numbers, a new mandatory requirement or
  first-person claim, a dropped qualifier, reversed advice, a new named term, a
  false "already completed" claim, markup/register changes, a rewrite outside the
  length band (`max(6, 0.65*original)`..`min(95|250, 1.6*original)` words), and
  stock banned phrasing. Returns the normalized, evidence-preserving prose.
- `humanize_review(model, composed, endnote, rewrite, progress=None) -> (composed, endnote, audit, warnings)`:
  edits each comment body and each narrative letter paragraph (not the greeting,
  headings ending in `:` or signoff), keeps passages under six words, and never
  edits the two precise-date corrections (`mla_date_numeric`, `apa_date_numeric`).
  It retries a rejected candidate once, retains the original prose on repeated
  failure, and rolls the letter back if its word count leaves 138-382 or a
  humanized comment/letter pair shares a sentence the original pair did not share.
  `audit` records `enabled`, `mode="guarded"`,
  `provider`, `model`, `elapsed_seconds`, `attempted`, `rewritten`, `unchanged`,
  `retained`, `retries`, `truncated_attempts`, `pieces` and `detector_score=None`.
- `narrative_indices(endnote)`, `feedback_piece_count(composed, endnote)`,
  and the module regexes `QUALIFIERS`, `ADVICE_START`, `STARTERS`, `FACTS`,
  `CONTRACTIONS`.

### Reviewer-letter structure (`letter_format.py`)

- `PLAIN_HEADINGS`: recognized plain section names (e.g. "Thesis and overall
  focus", "Evidence and analysis") accepted without a trailing colon.
- `is_endnote_heading(text)` and `parse_reviewer_letter(text)`: split a saved or
  edited reviewer letter into native paragraphs without inventing punctuation.
  Shared by `writer`, `validate` and the portal feedback editor.

### Anti-AI stylometrics and pattern scrubber (`anti_ai_patterns.py`)

- `scrub_ai_tells(text: str, seed: int = 0) -> str`: Deterministic AST/Regex scrubber resolving 26 Wikipedia/blader AI writing tells (discourse markers, Not X but Y patterns, staged run-ups, stacked qualifiers, shallow -ing riders, copula avoidance, meta-references) and injecting natural contractions outside quotes. Anchored student quotes (`"..."`, `“...”`, `‘...’`) and `https://knowledge.thinkingstorm.com/` URLs are masked via nonces and protected from mutation.
- `audit_ai_tells(text: str) -> list[str]`: Audits feedback text for any remaining banned words or structural AI patterns outside protected quotes/URLs.
- Opener archetypes in `persona.py`: `classify_opener_archetype(text)` maps comments into 6 archetypes (`imperative_quote`, `socratic_check`, `contrastive_claim`, `conditional_fix`, `fragment_diagnosis`, `reader_anchor`) to enforce cadence oscillation and opener diversity.

### Release gate (`validate.py`, `style_guard.py`)

- `@dataclass ValidationReport`: `ok`, `errors`, `warnings`, `metrics`.
- `validate_deliverable(output_path, model, expected, comment_bodies, endnote_paragraphs, reviewer_name="Raunak Banga") -> ValidationReport`.
- `style_guard.StyleReport`, `check_text_block(texts, label="comments")`,
  `burstiness`, `repeated_ngram_ratio`, `opener_ratio`, `banned_hits`,
  `sentences`. Thresholds: `MIN_BURSTINESS_STD = 2.6`,
  `MAX_MEAN_SENTENCE = 32.0`, `MAX_NGRAM_REPEAT = 0.12`,
  `MIN_UNIQUE_OPENERS = 0.65`. Computes sentence length Coefficient of Variation (`cv`).

### Reporting and coverage (`report.py`, `coverage.py`, `word_layout.py`)

- `report.build_review(model, result, source_text, *, mode="academic", institution="", student_name="", reviewer_name="Raunak Banga", delivered_endnote=None) -> dict`:
  deterministic rubric, redline and executive summary;
  `PILLARS_ACADEMIC`, `PILLARS_ADMISSIONS`.
- `coverage.PageMap` (`method`, `starts`, `words_before`, `pages`, `page_for`),
  `coverage.page_map(model)`, `coverage.assess(model, composed, endnote)`,
  `coverage.copied_comment_sentences(composed, endnote)` (the >=8-word comment
  sentences repeated in the letter), `coverage.PROFILE` (loaded from
  `knowledge/review_quality_profile.json`).
- `word_layout.word_paragraph_pages(path: str | Path) -> tuple[list[int], int] | None`:
  queries Microsoft Word via local COM automation (`Word.Application`) in read-only
  mode on Windows to extract exact paragraph start page numbers and true page
  count for page-aware coverage mapping. Results are cached by `(path, mtime)`.
  Returns `None` on non-Windows hosts, when Word is unavailable, or when
  `TS_WORD_PAGINATION=0`.

### Ingestion, segmentation and source material (`ingest.py`, `segmenter.py`, `source_material.py`)

- `ingest.pdf_text_to_paragraphs(raw)`, `ingest.plain_text_to_paragraphs(raw)`.
- `segmenter.Sentence`, `split_sentences(text, min_chars=12)`,
  `sentence_containing`, `first_sentence`, `last_sentence`, `content_words`.
- `source_material.previous_letter_start(paragraphs)`,
  `source_material.remove_previous_letter(source, target)`.

### Diagnostics and the optional local backend (`diagnostics.py`, `local_model.py`)

- `diagnostics.entries()`, `by_rule()`, `for_rule(rule_id)`, `all_for_rule`,
  `status(diagnostic_id)`, `coverage()`, `STATUSES`, `MAP_PATH`.
- `local_model.LocalReviewError`, `canonical_category`, `configuration`,
  `parse_model_json`, `chat`, `examples_for`, `decode_comments`,
  `closing_examples_for`, `comment_rows`, `apply_editorial_changes`,
  `compose_local`, `decode_endnote`, `CATEGORIES`, `SYSTEM`.

### Entry points (`cli.py`, `watch.py`)

- `cli.main(argv=None) -> int`, `cli.build_parser()`, `cmd_review`,
  `cmd_batch`, `cmd_watch`, `cmd_dry_run`, `cmd_selftest`, `cmd_audit`.
  Module invocation: `python -m engine.review.cli <command>`. `main` calls
  `engine.review_runtime.apply_runtime_defaults()` before dispatch and
  `_feedback_rewriter()` resolves `engine.feedback_humanizer.configured_rewriter()`
  for `review`, `batch` and `watch`. `review`/`batch` exit 3 (not 0) when the
  result is flagged `needs_review`.
- `watch.process_once(inbox, outbox, reviewer, initials, style, feedback_rewriter=None)`,
  `watch.run_watcher(inbox, outbox, interval=10, reviewer="Raunak Banga", initials="RB", style="auto", once=False, feedback_rewriter=None)`,
  `watch.STOP_FILE = "STOP"`, `watch.LEDGER = "processed.json"`.

### Progress notifications (`progress.py`)

- `emit_progress(callback, stage, **fields)`: calls `callback({'stage': ..., ...})`
  when a callback is supplied and swallows observer exceptions, so a UI listener
  can never change review correctness.
- Stage vocabulary used by the pipeline and portal: `reviewing`,
  `feedback_ready` (`total_passages`, `completed_passages`), `humanizing`
  (plus `editing_eta_seconds`), `retry`, `document`, `document_ready`.

## Invariants

- **Manuscript preservation**: the writer only splits runs; the concatenated
  text of every paragraph must be character-identical to the loaded model. The gate
  fails with `manuscript text changed in N paragraph(s)` on any drift, and
  tolerates exactly one appended empty paragraph when it holds the new
  `endnoteReference` for endnote id 1.
- **Anchor fidelity**: every delivered comment owns exactly one
  `commentRangeStart`/`commentRangeEnd` pair whose collected text, whitespace-
  normalized, equals the `Finding.quote` the reviewer saw. A missing or
  duplicate anchor is a hard error.
- **Anchorability**: comments are filtered through `normalize_span` +
  `can_anchor` before composition. Losing more than `max(2, len(selected)//4)`
  comments, or losing any comment on the `local` backend, aborts the run.
- **Comment budget**: the gate accepts 1-120 own comments; each body is 6-95
  words, ends with terminal punctuation, contains no double space, no banned
  phrasing, and does not repeat its category label. The written body must equal
  the composed/humanized body exactly. `CATEGORY_CAPS`/`RULE_CAPS`
  are per-category and per-rule-id caps (widened by `comprehensive=True`), not
  per-page limits. Page density is advisory: `coverage.assess` compares the draft
  with `knowledge/review_quality_profile.json` and its messages are appended to
  `validation.warnings`; a coverage shortfall never fails the gate. Fewer than
  three supported findings is a warning, not an error.
- **No overlapping own ranges**: two of our comment ranges may not overlap in a
  paragraph (pre-existing reviewer ranges may, because a second pass appends).
- **Comment-reference adjacency**: every `commentRangeEnd` must be followed
  immediately by a `w:r` carrying a `commentReference` with the same id.
- **Endnote contract**: endnote `w:id="1"` exists, its paragraphs equal the
  composed (or humanized) letter exactly, it opens with `Dear `, contains the
  reviewer signature, has 1-3 recognized domain headings, meets the minimum
  length for that heading count (60/90/120 words), and every non-blank run is
  Times New Roman, red `FF0000`, `w:sz=24` (12 pt). A heading is either a single
  line ending in `:` or a known plain name in `letter_format.PLAIN_HEADINGS`;
  the composer always emits the colon form, and the looser check exists so an
  edited letter that keeps the heading name is still accepted.
- **Link allowlist**: every comment hyperlink target must start with
  `https://knowledge.thinkingstorm.com/`; `links.FALLBACK` is used for
  unmapped categories rather than dropping the label.
- **Determinism**: no randomness or network input affects findings, selection or
  composition on the rules path; the model fingerprint is `sha1` of
  whitespace-normalized non-reviewer text, so the same draft always produces the
  same model and comment ordering. One clock input remains: `analysis.py` freezes
  `_CURRENT_YEAR = datetime.now(timezone.utc).year` at import and the reference
  check rejects years greater than `_CURRENT_YEAR + 1`, so findings can change at a
  year boundary or between processes started in different years. The optional
  `feedback_rewriter` is the only other input that can change delivered prose;
  it never changes findings, anchors, ordering or categories.
- **Humanization is guarded**: no candidate reaches the document unless
  `validate_rewrite` accepted it. Masked facts (names, quotations, URLs, numbers,
  dates, `[[KEEP_*]]`) are restored byte-for-byte, the original prose is kept when
  the guard rejects twice, truncated output is never delivered, and retained
  passages downgrade `quality.needs_review` and add a warning instead of failing
  silently. The letter is rolled back as a unit if its length leaves 138-382 words
  or if a humanized comment and letter share a sentence that the original pair did
  not share.
- **Reviewer material is not student prose**: paragraphs from a recognized
  previous review letter become `region == "reviewer_note"` and are excluded
  from `full_text`, `word_count` and analysis; rhetorical feedback may not be
  anchored to `references` or `reviewer_note` regions.
- **Fail-closed delivery**: if validation reports any error, the output `.docx`
  is unlinked and `PipelineError` is raised; a half-correct file is never
  returned.
- **Package canonicity**: `_native_package_problems` rejects duplicate
  relationships to the same part, comment ids absent from `comments.xml`, and
  content after `w:sectPr` (Word would offer to repair and drop the comments).
- **Existing comments are preserved**: pre-existing comment ids are kept and new
  ids start at `max(existing)+1`; a file that already has comments is rejected
  unless `allow_existing_comments=True`.
- **Offline by default**: the rules backend makes no network call. The `local`
  backend must resolve to an `http` loopback host (`127.0.0.1`, `localhost`,
  `::1`) and a provider in `{ollama, strata, llamacpp}`; anything else raises
  `LocalReviewError` rather than falling back to a cloud model.
- **Word layout extraction**: `word_layout.word_paragraph_pages` opens input `.docx`
  read-only (`$false, $true`), does not save or modify it, and terminates the COM
  instance cleanly in a `finally` block. Returns `None` on non-Windows hosts, missing
  Word, or when `TS_WORD_PAGINATION=0`.

## Side Effects

- **Disk, deliverable**: writes `<stem>_commented.docx` into `output_dir`
  (default: the input's parent). Without `overwrite=True`, an existing name is
  suffixed `-2`, `-3`, ... up to `-99`.
- **Disk, sidecar**: writes `<stem>_commented.review.json` next to the
  deliverable containing fingerprint, style, essay type, findings, comments,
  endnote, `review_quality` (including humanizer warnings and `needs_review`),
  `generation` (backend, `detector_score`, `humanization` audit when a rewriter ran),
  `editorial_status` and validation errors/warnings/metrics. The sidecar is written
  before the gate decides, so a rejected run still leaves its diagnostic JSON but no
  `.docx`.
- **Disk, deletion**: deletes the produced `.docx` when the release gate fails
  (`OSError` from the unlink is swallowed).
- **Temporary files**: `writer.write_deliverable` and
  `source_material.remove_previous_letter` create `tempfile.mkdtemp()` staging
  directories under the system temp root and remove them in `finally`.
- **In-memory mutation**: `explode_runs` and `anchor_comment` mutate the
  in-memory `python-docx` tree (`model.doc`) supplied by the caller; the source
  file on disk is only read, never opened for writing.
- **Injected humanizer transport**: when the caller passes a rewriter with a
  `session()` context manager, the pipeline enters it for the whole edit pass. The
  repository transport (`engine.feedback_humanizer.LocalHumanizer`) takes a
  non-blocking file lock at `output/humanizer/review.lock`, issues loopback HTTP
  (`/v1/models`, `/slots`, `/completion` or `/v1/chat/completions`) and enforces a
  wall-clock budget; none of that code is imported or called when
  `feedback_rewriter=None`.
- **Progress callbacks**: `pipeline.review_document` calls `progress.emit_progress`
  for `reviewing`, `feedback_ready`, `humanizing`/`retry`, `document` and
  `document_ready`; observer exceptions are swallowed.
- **Directories, watcher**: `watch.process_once` creates `inbox`, `outbox`,
  `inbox/done`, `inbox/failed`; moves processed files into `done/`, rejected
  files into `failed/` with a `<stem>.error.txt`, maintains
  `outbox/processed.json` and rewrites `outbox/watcher_heartbeat.json`.
- **Local model HTTP**: `local_model.chat` issues an `http` request to the
  loopback endpoint from `configuration()`; it never contacts a remote host and
  refuses to truncate manuscript text when the context budget is exceeded.
- **COM automation (Windows)**: `word_layout.word_paragraph_pages` launches a
  headless `Word.Application` COM instance via PowerShell on Windows to compute
  paragraph page numbers when `TS_WORD_PAGINATION` is enabled.
- **Imports of repository data**: `coverage.PROFILE` reads
  `knowledge/review_quality_profile.json` and `kb` reads
  `knowledge/thinkingstorm_kb_v2.json` at import/call time (read-only).
- **Console output**: CLI commands write progress and results to stdout, and
  rejection reasons to stderr.

## Verification

- Run (repository root): `python -m unittest discover -s tests`
- Focused checks: `python -m unittest tests.test_review_pipeline tests.test_deliverable_integrity tests.test_native_ooxml tests.test_review_grounding tests.test_feedback_humanizer tests.test_review_progress tests.test_review_coverage`
- Humanizer/pipeline interaction: `python -m unittest tests.test_feedback_humanizer`
- Manual smoke (no document written): `python -m engine.review.cli dry-run tests/fixtures/<fixture>.docx`
- Deliverable audit: `python -m engine.review.cli audit <deliverable>.docx`
