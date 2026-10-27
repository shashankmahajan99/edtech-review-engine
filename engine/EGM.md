# engine: Review Engine and Deliverable Builders

## Overview

`engine/` holds the Python review engine for the platform. It contains three
generations of deliverable builders that coexist:

1. `engine/review/` — the current, deterministic, offline review pipeline. It is
   the supported path and the only one the release gate protects.
2. `processor.py` + `deep_pipeline.py` + `prompts.py` — the portal-facing report
   builder. `ReviewProcessor.analyze_text` is deterministic by default and
   derives its rubric from `engine.review`; a model call happens only when
   `APEX_ENABLE_LLM` is `1/true/yes` **and** an API key is present.
3. `thinkingstorm_engine.py`, `word_native_comments.py`,
   `openxml_track_changes.py`, `anti_ai_humanizer.py` — legacy comment/endnote
   and tracked-change generators. `thinkingstorm_engine`'s own docstring marks it
   as superseded by `engine/review`; it is retained for the portal and fixtures
   that still import it.

Two deployment-side modules sit beside the builders: `review_runtime.py`
(`apply_runtime_defaults()` turns an optional JSON profile into
`TS_REVIEW_BACKEND`/`TS_HUMANIZER` defaults) and `feedback_humanizer.py`
(`LocalHumanizer`, the loopback-only raw-completion transport used for optional
feedback rewriting). Neither changes the offline review path on its own.

The comment/endnote and tracked-change builders share one rule: the student's
manuscript text is not rewritten. The current path only splits runs, and the
legacy builders inject comments and `<w:ins>`/`<w:del>` markup around existing
runs. `anti_ai_humanizer.py` no longer rewrites anything: its old rewrite helpers
(`sanitize_ai_vocabulary`, `inject_human_burstiness`, `humanize_editorial_comment`)
are now compatibility no-ops that return the supplied prose unchanged, and the
module keeps only `measure_burstiness`, the banned-vocabulary tables and the
legacy tutor-letter template. Optional rephrasing of *feedback* lives in
`engine/review/humanization.py` behind an injected rewriter and its preservation
guards; it can never touch manuscript text.

## Problem & Scope

- `engine/` is the only place where manuscript diagnosis and Word deliverable
  assembly happen; `engine/review/` is the release-gated path and the portal imports
  it lazily.
- Three builder generations coexist because the portal and fixtures still import the
  legacy modules: `engine/review` (current), `processor` + `deep_pipeline` (portal
  report builder), and `thinkingstorm_engine` + the OpenXML helpers (legacy comment
  and tracked-change generators).
- Scope is a single `.docx` in and a `.docx`/`.html` out; there is no service, queue
  or database except the optional self-prompting registry.
- The directory also carries the optional self-prompting framework, the deployment
  runtime defaults and the humanizer transport. None of the three belongs to the
  release-gated path: the runtime profile is read by launchers, the self-prompting
  registry is admin-only, and the humanizer is injected by the portal/CLI only when
  `TS_HUMANIZER=local`.
- The legacy `anti_ai_humanizer` helpers are kept for API compatibility but are now
  identity functions; rewriting feedback is a separate, guarded stage in
  `engine/review/humanization.py`.

## Goals & Non-Goals

- Goal: preserve the student's manuscript text while adding native comments,
  endnotes and tracked changes.
- Goal: keep `engine/review` deterministic and offline; keep model use opt-in and
  outside the release gate.
- Goal: keep the package surface small — `ReviewProcessor`, the two prompt constants
  and `engine/review`'s `review_document`/CLI entry points.
- Goal: make deployment defaults explicit rather than implicit: a launcher calls
  `review_runtime.apply_runtime_defaults()` and the humanizer is created only by
  `feedback_humanizer.configured_rewriter()` when `TS_HUMANIZER=local`.
- Non-goal: consolidating the three generations in this change; the legacy modules
  stay until the portal stops importing them.
- Non-goal: model-graded review on the default path. `ReviewProcessor.analyze_text`
  falls back to the deterministic rubric when the opt-in or key is missing.
- Non-goal: a public API. `engine/cli.py` and `engine.review.cli` are the supported
  entry points.
- Non-goal: unguarded prose rewriting. The legacy helpers never edit text, and the
  only rewriting stage requires an injected transport plus `humanization.py`'s
  preservation checks.

## Alternatives Considered

- Deleting the legacy builders now: rejected because the portal's manual Studio path
  and fixtures import `thinkingstorm_engine`; the risk is divergent output between
  generations, so new behaviour belongs only in `engine/review`.
- One universal builder instead of three: deferred; `engine/review` cannot emit the
  legacy endnote typography or the portal's HTML report without porting those
  fixtures first.
- Model-first review: rejected for the default path because determinism and the
  release gate are the product's safety property; `ReviewProcessor` keeps a
  deterministic fallback.
- Moving the humanizer into `engine/review` as an unguarded prose rewriter: rejected.
  The accepted design is the opposite: the transport stays in
  `engine/feedback_humanizer.py`, and `engine/review/humanization.py` owns only the
  offline guards, so the review package never imports a model client directly.
- Deleting `anti_ai_humanizer`'s substitution helpers: rejected because
  `thinkingstorm_engine` and `deep_pipeline` still import them; making them no-ops
  preserved those imports without letting them change delivered prose.
- Reading runtime configuration inside `review_document`: rejected; direct pipeline
  calls stay offline and deterministic, and only launchers opt into profile defaults.

## Risks & Mitigations

- Divergent output between the three generations: a fix in one builder does not
  reach the others. Mitigation is to keep new behaviour in `engine/review` and mark
  each generation's status here.
- A caller importing a legacy module bypasses `validate_deliverable`; only
  `engine/review` is release-gated. Mitigation is the portal's 422 path and the
  explicit "legacy" labels in this contract.
- A future edit could make the legacy helpers rewrite prose again or route the
  humanizer around `engine/review/humanization.py`. Mitigation is the no-op contract
  documented here, the guarded stage's `validate_rewrite`, and
  `tests.test_feedback_humanizer`, which asserts the helpers return their input.
- The optional self-prompting framework opens the shared SQLite file at construction
  and seeds five templates, so importing it has an effect. Mitigation is to
  construct it only in the admin/self-prompting path.
- `apply_runtime_defaults()` mutates `os.environ` with `setdefault`. Mitigation is
  that it never overrides an explicit variable, validates the profile strictly and
  raises `RuntimeError` for an unknown or malformed profile instead of silently
  falling back.
- The humanizer transport can hang or be busy; it refuses to queue. Mitigation is
  the non-blocking lock, the `/slots` check, the wall-clock budget and
  `HumanizerUnavailable`, which the pipeline converts into `PipelineError` so no
  partial deliverable ships.
- Model calls in `ReviewProcessor` and `DeepReviewPipeline` can fail or cost money;
  the fallback logs a warning and returns the deterministic report.

## Interface

### Package surface (`__init__.py`)

- `ReviewProcessor`, `ACADEMIC_REVIEW_SYSTEM_PROMPT`,
  `ADMISSIONS_SOP_SYSTEM_PROMPT` are re-exported via `__all__`.

### Review processor (`processor.py`)

- `class ReviewProcessor(api_key: Optional[str] = None, model: str = "gpt-4o")`:
  reads `OPENAI_API_KEY` when `api_key` is omitted and computes
  `llm_opt_in` from `APEX_ENABLE_LLM`.
- `analyze_text(text, mode="academic", prompt_requirements="") -> dict`:
  deterministic rubric unless the LLM opt-in and a key are both present.
- `generate_annotated_docx(original_text, review_data, output_path)` and
  `generate_html_report(review_data, output_path)`: the two portal artifacts.

### Prompt contracts (`prompts.py`)

- `ACADEMIC_REVIEW_SYSTEM_PROMPT`: 4-criterion academic rubric as a JSON schema
  (`overall_score`, `category_scores`, `executive_summary`,
  `top_action_items`, `line_edits`).
- `ADMISSIONS_SOP_SYSTEM_PROMPT`: 4-dimension admissions rubric over the same
  payload shape.

### Deep review pipeline (`deep_pipeline.py`)

- Pydantic payload models: `CategoryScore` (`score` 0-25, `max` 25,
  `verdict`), `LineEdit` (`original_text`, `suggested_replacement`,
  `issue_type`, `explanation`), `DeepReviewPayload` (`overall_score` 0-100,
  `category_scores`, `executive_summary`, `top_action_items`, `line_edits`,
  `tutor_overview_letter`).
- `class DeepReviewPipeline(api_key=None, model="gpt-4o")` with
  `execute_3pass_review(manuscript, mode="admissions", target_institution="", counselor_brief="") -> DeepReviewPayload`.

### Legacy ThinkingStorm deliverable (`thinkingstorm_engine.py`)

- `class ThinkingStormAutomator(reviewer_name="Raunak Banga", initials="RB")`
  with `analyze_manuscript(text, student_name="Student") -> (comments, domains)`,
  `_anchor_comment_to_runs(...)`, and
  `generate_reviewed_docx(input_docx, output_docx, student_name="Student", custom_comments=None, custom_domains=None, custom_endnote_text=None) -> str`.
- Module helpers: `extract_student_first_name(text_or_paragraphs, default="Student")`,
  `parse_custom_comments_text(raw_text) -> list[dict]`,
  `parse_custom_endnote_text(raw_endnote, student_first_name="Student", reviewer_name="Raunak Banga") -> list[str]`.
- `THINKINGSTORM_KNOWLEDGE_BASE`: category -> `knowledge.thinkingstorm.com` URL
  map shared with `engine/review/links.py`.

### Native margin comments (`word_native_comments.py`)

- `class NativeWordCommentEngine(author="Senior Admissions Reviewer", initials="SAR")`
  with `inject_native_comments(input_docx, output_docx, comments_list) -> str`.
  Each item supplies `target_text`, `category`, `comment_text`, `link_url`.

### Tracked changes (`openxml_track_changes.py`)

- `class WordTrackChangesEngine(author="Apex Admissions Reviewer")` with
  `create_tracked_insertion(text)`, `create_tracked_deletion(text)`,
  `apply_tracked_replacement(paragraph, original_phrase, replacement_phrase, explanation=None)`,
  `process_document(input_path, output_path, line_edits) -> str`,
  `create_trivium_certified_document(text, output_path, line_edits, student_name="Applicant", institution="", submission_id="", rubric_scores=None, tutor_letter=None) -> str`,
  `create_tracked_docx_from_text(text, output_path, line_edits) -> str`.
  Revision ids come from a monotonic `_get_next_id()` counter starting at 1;
  timestamps are UTC `"YYYY-MM-DDTHH:MM:SSZ"`.

### Voice statistics and legacy editorial helpers (`anti_ai_humanizer.py`)

- `measure_burstiness(text) -> (mean, std_dev, burstiness)`; these are rhythm
  statistics, not an authorship detector.
- Compatibility no-ops (kept for `thinkingstorm_engine` and `deep_pipeline`):
  `sanitize_ai_vocabulary(text)` returns `text`,
  `inject_human_burstiness(sentences)` returns `list(sentences)`, and
  `humanize_editorial_comment(original_comment, author_role="Trivium / ThinkingStorm Senior Reviewer")`
  returns `original_comment.strip()`.
- `build_thinkingstorm_tutor_overview(student_name, institution, prompt, word_count, scores, reviewer_name="Academic Admissions Specialist", specific_observations=None)`:
  the legacy fixed-shape tutor letter (header block, greeting, canned priority
  bullets when `specific_observations` is empty, signoff). It is not detector-aware
  and is not used by the release-gated path.
- Data: `BANNED_AI_VOCABULARY` (set of classifier-triggering words),
  `HUMAN_EDITORIAL_REPLACEMENTS` (phrase -> human editorial idiom). The tables are
  retained as reference data; the functions above no longer apply them.

### Feedback humanizer transport (`feedback_humanizer.py`)

- `class HumanizerUnavailable(RuntimeError)`: configuration, readiness, budget or
  protocol failure; the pipeline turns it into a rejected review.
- `class LocalHumanizer(path=None)`: reads `TS_HUMANIZER_CONFIG` or
  `output/humanizer/config.json` and validates the keys (`base_url`, `model`,
  `model_name`, `prompt_path`, `budget_seconds`, `call_timeout_seconds`,
  `provider`). `base_url` must be a loopback `http` origin; the provider is
  `completion` (`thinkingstorm-humanizer`, pinned prompt fingerprint
  `PROMPT_FINGERPRINT = "cc51d66b4c593fbe"`) or `instruct` (`thinkingstorm-editor`);
  `prompt_path` must be absolute; budgets are capped at 180 s/30 s.
- `prompt(text)`, `_request(path, payload=None)`, `session()` (non-blocking lock at
  `output/humanizer/review.lock`, `/v1/models` and `/slots` readiness checks,
  deadline), `__call__(text)` -> rewritten text; raises `TruncatedRewrite` on a
  length-limited reply and rejects passages over 6000 bytes.
- `configured_rewriter()`: returns `None` when `TS_HUMANIZER` is unset/`off`,
  `LocalHumanizer()` for `local`, and raises `HumanizerUnavailable` otherwise.
- `ROOT` (repository root) and `PROMPT_FINGERPRINT` constants.

### Deployment runtime defaults (`review_runtime.py`)

- `apply_runtime_defaults()`: reads `TS_RUNTIME_PROFILE` or
  `output/review-runtime.json` and `setdefault`s `TS_REVIEW_BACKEND`
  (`rules`/`local`), `TS_HUMANIZER` (`off`/`local`) and `TS_HUMANIZER_CONFIG`.
  A malformed profile raises `RuntimeError`; a missing explicitly configured
  profile raises `RuntimeError`; with no profile, the presence of
  `output/local-model/config.json` only defaults the backend to `local`. Explicit
  environment variables always win.
- `ROOT`: repository root used to resolve the default paths.

### Command line (`cli.py`)

- `main()`: `python -m engine.cli --input <path> --mode {academic,admissions} --outdir output`.
  Writes `<stem>_annotated_review.docx` and `<stem>_executive_report.html`.

### Self-prompting framework (`self_prompting_framework.py`)

- `@dataclass SelfPromptIteration` and `@dataclass SelfPromptingResult`
  (`run_id`, `task_goal`, `domain`, `target_institution`, `initial_score`,
  `final_score`, `score_delta_pct`, `iterations`, `converged`, `final_payload`,
  `total_time_ms`, `production_ready`).
- `class SelfPromptCritic` with `CRITERIA_WEIGHTS` (verbatim anchoring 0.25,
  voice preservation 0.25, institutional fit 0.20, pedagogical value 0.20,
  rubric coherence 0.10) and `evaluate(manuscript, candidate_output, target_institution="")`.
- `class SelfPromptingFramework(db_path=None)` with `CONVERGENCE_THRESHOLD = 91.0`,
  `MAX_SELF_PROMPT_CYCLES = 3`, `formulate_goal_and_context(...)`,
  `generate_meta_prompt(...)`, `execute_self_prompted_run(manuscript, domain="admissions", target_institution="", counselor_brief="")`,
  `get_registry_prompts()`, `get_recent_runs(limit=10)`, `get_aggregate_metrics()`.
- Default database: `orchestrator/desk_jobs.db` (`PROJECT_ROOT/DB_PATH`).

### Assets in this directory

- `SELF_PROMPTING_SPEC.md` — design note for the self-prompting framework.
- `test_track_changes.py` — ad-hoc executable script for the legacy track-changes
  engine; it is not part of the `unittest` discovery suite.

### Subdirectories

- [review](./review/EGM.md): the deterministic review pipeline (`review_document`,
  Word comment/endnote writer, release gate, CLI and watcher).

## Invariants

- **Document preservation**: `NativeWordCommentEngine.inject_native_comments`
  and `ThinkingStormAutomator.generate_reviewed_docx` never rewrite student
  text; they only add `commentRangeStart`/`commentRangeEnd`/`commentReference`
  and package parts. `WordTrackChangesEngine` wraps existing text in
  `<w:ins>`/`<w:del>` and never replaces the paragraph text. The current pipeline
  enforces the same rule through the release gate in `engine/review/validate.py`.
  The legacy `anti_ai_humanizer` helpers now preserve their input as well, so no
  module in `engine/` rewrites manuscript prose.
- **Humanizer is a guarded, injected stage**: `engine/review/humanization.py` is
  the only place feedback wording may change. It masks facts, validates every
  candidate, keeps the original prose when a rewrite is rejected twice, never
  delivers truncated output, and downgrades `needs_review` when a passage is
  retained. `feedback_humanizer.LocalHumanizer` only talks to a loopback `http`
  endpoint and refuses to queue behind a busy slot; the review package never
  imports it directly.
- **Legacy helpers are non-mutating**: `sanitize_ai_vocabulary`,
  `inject_human_burstiness` and `humanize_editorial_comment` return their input
  unchanged. `BANNED_AI_VOCABULARY`/`HUMAN_EDITORIAL_REPLACEMENTS` remain reference
  data, not an applied transformation.
- **Runtime defaults never override**: `apply_runtime_defaults()` uses
  `os.environ.setdefault`, validates the profile keys/values strictly, and raises
  `RuntimeError` for an invalid or missing explicitly configured profile rather
  than guessing.
- **Exact-span anchoring**: a comment range covers only the target phrase, never
  the whole paragraph. `_anchor_comment_to_runs` and
  `openxml_track_changes.apply_tracked_replacement` split the surrounding runs
  so the highlighted span matches the quoted words.
- **Portal is model-optional**: `ReviewProcessor.analyze_text` returns the
  deterministic report unless `APEX_ENABLE_LLM` is set *and* an API key exists.
  A failed model call logs a warning and falls back to the deterministic engine
  rather than failing the request.
- **Verbatim line edits**: `DeepReviewPipeline._extract_verbatim_edits` only
  emits a `LineEdit` when the `original_text` exists verbatim in the manuscript
  (case-insensitive search, original casing recovered); the critic scores
  `verbatim_anchoring` accordingly.
- **Derived, not invented, scores**: `DeepReviewPipeline._synthesize_rubric_evaluation`
  computes each pillar from counted facts (word count, number of validated
  edits) rather than from free text, so the same manuscript always produces the
  same score.
- **Rubric arithmetic**: `CategoryScore.score` is bounded 0-25 with `max` 25 and
  `DeepReviewPayload.overall_score` is bounded 0-100 (Pydantic `Field` ge/le).
  These are independent per-field bounds; the model has no cross-field validator,
  so `overall_score` need not equal the sum of `category_scores`. Consistency comes
  only from `_synthesize_rubric_evaluation`; a model-supplied payload parsed into
  `DeepReviewPayload` can be internally inconsistent and must not be treated as a
  pillar/overall invariant.
- **Endnote typography (legacy builder)**: ThinkingStorm endnotes are produced as
  native `word/endnotes.xml` content, Times New Roman, 12 pt
  (`w:sz w:val="24"`), red `FF0000`, double-spaced (`w:line="480"`,
  `w:lineRule="auto"`), with a dynamic greeting and the reviewer signature;
  repeat runs update the existing endnote rather than duplicating id 1.
- **Knowledge-base host allowlist**: every category link points at
  `https://knowledge.thinkingstorm.com/...`; the current pipeline enforces this
  in `validate_deliverable` via `engine.review.links.is_allowed`.
- **Revision identity**: tracked changes carry a monotonically increasing
  `w:id`, a fixed author, and a UTC timestamp so Word can accept or reject each
  edit independently.
- **Determinism boundary**: the current review path is deterministic when no
  `feedback_rewriter` is injected. The only optional rewriter is the loopback
  transport documented above, and its output passes the offline preservation
  guards before it can reach a document; nothing in `anti_ai_humanizer` adds
  randomness any more.
- **Legacy status**: `thinkingstorm_engine.py` is documented in-file as a legacy
  generator superseded by `engine/review`; new behaviour belongs in
  `engine/review`, not in the legacy builders.

## Side Effects

- **Disk, portal artifacts**: `ReviewProcessor.generate_annotated_docx` and
  `generate_html_report` write a `.docx` and an `.html` file at the caller's
  paths; `engine/cli.py` creates `--outdir` (default `output/`) first.
- **Disk, temp files**: `ReviewProcessor._generate_heuristic_report` builds a
  temporary `.docx` via `tempfile.NamedTemporaryFile(delete=False)`, runs the
  review engine over it, and unlinks it in `finally`.
- **Disk, zip rewriting**: the legacy OpenXML builders extract an input `.docx`
  into `tempfile.mkdtemp()`, edit `word/document.xml`, `word/comments.xml`,
  `word/endnotes.xml`, `[Content_Types].xml` and the relationship parts, then
  repackage to the output path and remove the staging directory.
- **Disk, SQLite**: `SelfPromptingFramework.__init__` opens
  `orchestrator/desk_jobs.db` and creates the `self_prompt_registry` and
  `self_prompt_runs` tables, seeding five default meta-prompt templates on first
  use; `_record_run` inserts run telemetry.
- **Network, three independent opt-ins**: the OpenAI client is instantiated only
  inside `ReviewProcessor.analyze_text` when `APEX_ENABLE_LLM` is enabled and a key
  is present. `engine.review.local_model.chat` opens an HTTP request to
  the loopback endpoint in `output/local-model/config.json` whenever
  `TS_REVIEW_BACKEND=local` (it does not consult `APEX_ENABLE_LLM`), and refuses to
  exceed the configured context/token budget rather than truncating manuscript
  text. Finally, `feedback_humanizer.LocalHumanizer` calls the loopback
  `output/humanizer/config.json` endpoint only when `TS_HUMANIZER=local`
  (`configured_rewriter()` returns `None` for `off`). All three are optional and
  none may be assumed on by default.
- **Disk, humanizer lock**: `LocalHumanizer.session()` creates
  `output/humanizer/` and holds a non-blocking OS lock on
  `output/humanizer/review.lock` for the duration of a review; a second review is
  refused with `HumanizerUnavailable` instead of waiting.
- **Environment, runtime defaults**: `review_runtime.apply_runtime_defaults()`
  mutates `os.environ` (`TS_REVIEW_BACKEND`, `TS_HUMANIZER`,
  `TS_HUMANIZER_CONFIG`) with `setdefault`. Launchers (`run_portal.py`,
  `engine.review.cli`) call it; direct `review_document` calls do not.
- **In-memory mutation**: `WordTrackChangesEngine` mutates `python-docx`
  paragraph objects and the parser tree under `xml.etree.ElementTree` before
  saving; `watch`/pipeline consumers must not assume the input element tree is
  unchanged after a build.
- **Console output**: `engine/cli.py` prints progress, the overall score and the
  resolved output paths; the processor prints warnings when the optional model
  call or the deterministic report fails; `engine.review.cli` prints
  `GENERATED`/`NEEDS REVIEW` and exits 3 for a flagged review.

## Verification

- Run (repository root): `python -m unittest discover -s tests`
- Relevant suites: `tests.test_review_pipeline`, `tests.test_deliverable_integrity`,
  `tests.test_native_ooxml`, `tests.test_feedback_humanizer`,
  `tests.test_review_progress`, `tests.test_studio_js` (the Studio page must keep
  parsing; it runs `node --check` on the rendered script).
- Legacy tracked-changes smoke test: `python -m engine.test_track_changes`
- Subtree contract: [review](./review/EGM.md)
