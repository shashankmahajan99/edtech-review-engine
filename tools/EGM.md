# Tools (Corpus Mining, Diagnostics, Integrity Gates, Local Model Ops)

## Overview

`tools/` is the offline toolbox behind the review engine's calibration and
quality gates. It has five jobs:

1. **Extract** — read native Word comments, anchored quotes and reviewer letters
   out of `.docx` files without touching them.
2. **Mine** — turn reviewed deliverables into the voice corpus and statistics
   (`style_corpus/`, `docs/VOICE_PROFILE.md`) that the deterministic composer is
   calibrated against, plus the paste-ready brief for an external model.
3. **Check contracts** — validate the ThinkingStorm knowledge base, classify
   every KB diagnostic against the analyser (the map gate is currently red — see
   Invariants), and audit a deliverable for genuinely native Word
   comments/endnotes.
4. **Operate local models** — index human examples, provision Ollama /
   llama-server / Strata runtimes, run and re-validate local reviews, and switch
   the running portal + watcher pair between rule-only, local-model and
   local-humanizer modes.
5. **Humanize** — `humanize_saved_review.py` rewrites an already-saved review's
   prose through the dedicated llama.cpp editor on `127.0.0.1:11437`, keeping its
   diagnoses, anchors, letter structure and native Word parts re-validated.

No hosted model is called and no provider API is used at review time. The only
HTTP traffic the runtime tools originate is a loopback call to the dedicated
humanizer server; the provisioning scripts download pinned artefacts from GitHub
releases and the Ollama registry. `portal/` imports `tools.endnote_extract`
(`portal/feedback_extract.py`) and `tools.strip_comments` (`portal/server.py`),
several tests import these modules, and `index_local_review_examples` imports
back from `portal.feedback_extract`, so the dependency is real in both
directions — signatures and import safety are contract, not CLI habit.

## Problem & Scope

- The deterministic engine needs calibration data (voice corpus, exemplars), a
  KB-to-analyser mapping, native-Word integrity checks, a local-model path for
  offline review experiments, and a way to restyle an approved review without
  paying for another inference run.
- `tools/` supplies those offline utilities; each is either imported by
  `portal/` or the test suite, or run by hand as a gate.
- In scope: `.docx` extraction and cleaning, corpus mining, KB validation, the
  diagnostic map, corpus audits, local Ollama / llama.cpp / Strata operations,
  the feedback-humanizer runtime and the deployment switch that selects it.
- Out of scope: the review decision itself (`engine/review/`), the guards that
  accept or reject a rewrite (`engine/review/humanization.py` lives in the
  engine, this package only drives it), portal routing and UI, and any hosted
  model call.

## Goals & Non-Goals

- Goal: read native Word parts (comments, endnotes) without modifying the
  deliverable; the one cleaner writes a new path, and every humanizer script
  writes a new deliverable.
- Goal: keep the KB honest — every diagnostic classified `mapped`, `human_only`
  or `no_rule`, with a non-zero exit on drift.
- Goal: produce the corpus artefacts the composer and `export_astra_brief`
  consume, reproducibly from local `.docx` folders.
- Goal: humanize a saved review without regenerating it — anchors, letter shape,
  quoted specimens, names, URLs and numbers are preserved or the passage is
  kept verbatim.
- Non-goal: completeness of the diagnostic map — the gate covers only part of
  the analyser (see Invariants).
- Non-goal: portability; several defaults hardcode `C:\Users\shashank\…` paths
  and the provisioning scripts are Windows-only.
- Non-goal: a silent fallback when the humanizer runtime is missing, busy or
  serving another model — `humanize_saved_review.py` fails instead of shipping
  unedited prose.

## Alternatives Considered

- Hosted model for corpus labelling or mapping: rejected — the engine is
  offline and deterministic, and `human_only` exists to route those judgements
  to a person.
- A hand-maintained `diagnostic_map.json`: rejected in favour of a generator,
  but the generator's vocabulary is narrower than the analyser's (see
  Invariants).
- `python-docx` for comment extraction: not used; `extract_review` parses the
  OOXML parts directly so native anchors survive.
- Stripping comments in place to build fixtures: rejected — `strip_comments`
  takes a distinct `dst` and never rewrites its input.
- Humanizing during generation instead of after it: the engine already owns that
  path; the standalone tool exists so an audited review can be restyled without
  a second model run and without re-deriving its diagnoses.
- Rewriting the saved `.docx` XML directly: rejected — the tool re-composes the
  comment bodies through `decode_comments` and `write_deliverable`, so anchors
  and native parts are rebuilt by the same writer the pipeline uses.
- One shared model runtime for review and humanization: rejected — the
  humanizer has its own llama.cpp server, port and single-slot lock so a busy
  reviewer model cannot corrupt an edit pass.

## Risks & Mitigations

- Silent corpus drift: `mine_voice_corpus` / `build_style_corpus` overwrite
  `style_corpus/*.json` and `docs/VOICE_PROFILE.md` on every run with no version
  pin. Mitigation: review the JSON diff before committing.
- The diagnostic gate is currently red (`para_drift`) and cannot see
  `pedagogy.py` rules, so its "mapped" coverage is not the analyser's.
- Local review outputs stay out of the source tree by convention
  (`output/local-model/…`, `scratch/`), not by a sandbox.
- `setup_local_reviewer.ps1` downloads Ollama from GitHub releases behind a
  pinned SHA-256, but weights arrive through `ollama pull`, outside that check;
  the humanizer setup script does verify its weights by SHA-256.
- Humanizer availability: the dedicated server is single-slot and
  non-blocking-locked, so a second concurrent review is rejected rather than
  queued. Mitigation: run one humanization at a time and watch
  `output/humanizer/server.stderr.log`.
- Humanizer model drift: the alias, provider and prompt fingerprint are pinned
  in `engine/feedback_humanizer.py`; replacing the weights without updating the
  config/checksums makes the script refuse to start.
- Restyled prose is still machine prose: the audit records
  `detector_score: null`, and retained passages raise a warning that forces
  `needs_review`.

## Interface

**Extractors (read-only)**
- `extract_review.extract(path: Path) -> dict` — `{file, size, comment_count,
  comments: [{id, author, initials, quote, text}], endnote, parts}`. Anchors are
  collected in document order, so comments nested in hyperlinks, smart tags and
  tables are captured. `main()` prints or `--json` dumps.
- `endnote_extract.paragraphs(path: Path) -> list[str]`;
  `body_letter(paras: list[str]) -> str` — locates the sign-off first
  (`SIGNATURE`), then walks back up to 45 paragraphs for the letter's start
  (`START`); returns `""` when either is missing. Its default script scans
  `C:\Users\shashank\Downloads\Doc examples`.

**Cleaner (writes a new `.docx`; not read-only)**
- `strip_comments.strip(src: Path, dst: Path)` — writes a cleaned copy with all
  comment parts, anchors, reference runs, relationships and content-type
  overrides removed. `DROP_PARTS` lists the parts that are dropped.

**Integrity gates**
- `audit_native.audit(path: Path) -> list[str]` — returns problem strings for:
  `w:sectPr` not last, comment-range id mismatch (start/end/reference),
  `comments.xml`/`endnotes.xml` id or relationship drift, missing author or
  text, missing `w:endnoteRef`, duplicate relationship ids or duplicate
  comments/endnotes relationship types, wrong content-type override, and inline
  `Editorial Note` text. Empty list means native-OK. The CLI defaults to three
  named exemplars under `output/review_v2/` (`janeen`, `andrea`, `kiran`
  `_raw_commented.docx`) and prints `missing` for absent paths.
- `audit_review_corpus.prepare(source, target) -> bool` — strips the example,
  then prefers `engine.review.source_material.remove_previous_letter` (which
  also removes the greeting); only when that finds nothing does it fall back to
  `body_letter` + paragraph-path truncation of the closing section. Raises
  `ValueError` when no reviewer letter is recognised.
- `audit_review_corpus.run(source: Path, output: Path) -> dict` — replays every
  example through `engine.review.pipeline.review_document`, cross-checks
  `endnote_evidence` against delivered comments, and writes `audit.json` plus
  `comparison.html` with per-document coverage/depth proxies
  (`coverage_and_depth_met`, `needs_editorial_review`) — measured proxies, not a
  detector score. CLI: `python tools/audit_review_corpus.py SOURCE --out
  scratch/corpus-audit`; exit code is non-zero if any file fails.

**Corpus mining**
- `mine_voice_corpus.main(folder: str)` — reads every `.docx` in the folder and
  writes `style_corpus/voice_corpus.json`, `style_corpus/voice_profile.json`
  and `docs/VOICE_PROFILE.md`. Module constants: `BANNED` (LLM vocabulary),
  `HEDGES`, `FIRST_PERSON`, `DIRECTIVES`, `LABEL_RE`, `CONTRACTIONS`. Helpers:
  `sentences`, `split_label`, `stats`, `is_specific`, `write_report`. The CLI
  default folder is the hardcoded `C:\Users\shashank\Downloads\Doc examples`.
- `build_style_corpus.main()` — same extraction over three hardcoded exemplar
  deliverables (Janeen, Andrea, Kiran) into `style_corpus/exemplars.json` and
  `style_corpus/exemplar_stats.json`; helpers `split_category`, `sent_lengths`.
- `export_astra_brief.main(--out docs/ASTRA_BRIEF.md)` — builds a paste-ready
  brief from `style_corpus/voice_corpus.json` + `voice_profile.json`; helpers
  `endnote_texts()` (reads the same three hardcoded paths),
  `stratified(comments, limit=64)` (seeded per label, so output is stable),
  `build(profile, corpus)`, schema constant `SCHEMA`.

**Diagnostics / KB contracts**
- `validate_kb.check(path: Path, legacy: bool = False)` — asserts the KB
  schema (see Invariants). CLI: `python tools/validate_kb.py
  knowledge/thinkingstorm_kb_v2.json [legacy.json]`.
- `build_diagnostic_map.main()` — joins `knowledge/thinkingstorm_kb_v2.json`
  diagnostics to analyser rules and writes `knowledge/diagnostic_map.json`.
  Classification tables: `MAPPED`, `HUMAN_ONLY`, `NO_RULE`, `LIT`. `_rules()`
  collects only double-quoted `Finding("…")` names from
  `engine/review/analysis.py` plus three aliases; it does not read
  `engine/review/pedagogy.py` or single-quoted findings, so its vocabulary is a
  subset of the analyser's (see Invariants).
- `report_diagnostic_coverage.main()` — prints
  `engine.review.diagnostics.coverage()` plus every `human_only` and `no_rule`
  entry with its reason. Current output: 120 diagnostics (43 `mapped`, 55
  `human_only`, 22 `no_rule`), 41 rules with a diagnostic, 37 emitted rules
  without one.

**Local model operations (top-level scripts, module-level CLIs)**
- `index_local_review_examples.build(source: Path, destination: Path)` — writes
  an anchored retrieval index (`--out output/local-model/examples.json`) with
  `{source, manuscript_probe, category, quote, feedback, letter}` rows; the
  first indexed comment of each document carries the letter. It skips `~$` lock
  files, requires `word/comments.xml`, and imports `portal.feedback_extract` and
  `engine.review.source_material` for extraction.
- `run_local_review.py` — strips the source, removes a previous letter, then
  calls `review_document(..., backend='local')`; `--config` sets
  `TS_LOCAL_CONFIG`, `--checkpoint` resumes a matching model/manuscript run.
- `make_local_review_checkpoint.py` — binds an existing review JSON to the
  manuscript fingerprint and writes a checkpoint; `--config` (required) sets
  `TS_LOCAL_CONFIG`, and the payload records `fingerprint`, `model`, `review`,
  `source_trace`.
- `revalidate_local_review.py` — rebuilds a saved review through the current
  formatter and `validate_deliverable` with no inference; takes the review JSON
  plus the model's letter trace, refuses to overwrite the manuscript and rejects
  a fingerprint mismatch.
- `create_text_reviewer.py` — derives a text-only Ollama alias from the
  installed Qwen weights (`ollama show --modelfile` → drop the second `FROM` →
  write `output/local-model/TextReviewer.Modelfile` → `ollama create`).
- PowerShell provisioning: `setup_local_reviewer.ps1` (providers
  `llamacpp`/`ollama`/`strata`, defaulting to `strata`, then indexing examples),
  `start_local_reviewer.ps1` (llama-server on 11435, using the downloaded Qwen
  language blob and Ollama's bundled CUDA runtime),
  `start_strata_reviewer.ps1` (Strata on 11436, writing
  `output/local-model/candidate-config.json`), `restore_strata_model.ps1`,
  `deploy_local_reviewer.ps1` (candidate config / fast mode → running portal +
  watcher).
- `deploy_local_reviewer.ps1` parameters: `-CandidateConfig`, `-Mode
  local|fast`, `-HumanizerMode local|off`. `-Mode fast` runs the rules backend
  and, with `-HumanizerMode local`, validates the humanizer `/health` and
  `/v1/models` before recording the `rules+local-humanizer` provider. It archives
  the previous profile and writes `output/review-runtime.json` (backend,
  humanizer, config path) atomically, stops only PID-verified portal/watcher
  processes, waits for port 8000 to be released, starts both children with logs
  under `output/deployments/<stamp>-local-reviewer/`, health-checks
  `/thinkingstorm`, and only then records `output/daemon_pids.json` and
  `deployment.json`.

**Feedback humanizer (runtime + tooling)**
- `humanize_saved_review.py` — module-level script (no functions, executes on
  import). CLI: `python tools/humanize_saved_review.py <review.json> --output
  <new.docx>`. It reads the saved payload (`input`, `style`, `fingerprint`,
  `comments`, `endnote`, `endnote_domains`, `endnote_evidence`, `reviewer`, plus
  the optional `generation` block it carries forward),
  refuses to overwrite the source, requires the fingerprint to match, re-expands
  runs, rebuilds comment bodies with `local_model.decode_comments`, drives
  `engine.review.humanization.humanize_review` with
  `engine.feedback_humanizer.LocalHumanizer`, re-assesses coverage, and writes
  the deliverable plus a sibling `<name>.review.json` (written with
  `path.with_suffix('.review.json')`) containing the humanization audit,
  before/after `humanization_comparison`, updated comments/endnote and the
  validation result.
- `setup_feedback_humanizer.ps1` — `-EditorSize 4b|9b`; downloads the pinned
  llama.cpp `b11335` CUDA zip and `cudart` zip plus the matching qwen3.5 blob
  (reusing `output/local-model/models/blobs/sha256-<digest>` when present),
  verifies every SHA-256, and expands into `output/humanizer/llamacpp`.
- `start_feedback_humanizer.ps1` — `-Port 11437`, `-StopStrata`, `-ModelType
  instruct|completion`, `-EditorSize 4b|9b`. It refuses to start when a
  different recorded model still holds `output/humanizer/server.pid`, when the
  port is listening, or when the weights hash differs; it optionally stops a
  verified Strata reviewer to free VRAM, launches `llama-server.exe` with
  `127.0.0.1`, `--offline`, `--no-webui`, one slot (`--ctx-size 4096`,
  `--parallel 1`), and writes `output/humanizer/config.json` with
  `{base_url, model, model_name, provider, prompt_path, budget_seconds: 180,
  call_timeout_seconds: 30}` — the exact contract `LocalHumanizer` validates.
- Sibling contracts: [bridge](../bridge/EGM.md),
  [orchestrator](../orchestrator/EGM.md), [scripts](../scripts/EGM.md).

## Invariants

- `extract_review`, `endnote_extract` and `audit_native` never write.
  `extract_review` reads `word/document.xml`, `word/comments.xml` and
  `word/endnotes.xml`; `endnote_extract` reads only `word/document.xml`.
- `strip_comments` must be given distinct `src`/`dst`; it rebuilds the zip from
  the source parts and never rewrites the input.
- `audit_review_corpus` refuses in-place work: `prepare` raises `ValueError`
  when `source == target`, `run` raises when the output directory is the source
  or sits inside it, and `prepare` refuses to analyse reviewer prose when no
  letter is recognised. The comparison HTML states explicitly that columns are
  separate reviews and that counts are proxies, not accuracy.
- `build_diagnostic_map` gates what it writes: it exits non-zero on an
  unclassified diagnostic, a mapped id absent from the KB, or a mapped rule name
  outside `_rules()`. It is **not** exhaustive over the analyser: the tool sees
  49 rule names (46 double-quoted `Finding("…")` ids in `analysis.py` + three
  aliases) while `engine.review.diagnostics._emitted_rules()` sees 78 (it also
  reads `pedagogy.py`'s 28 `_add(out, '…')` ids and the single-quoted
  `Finding('thesis_long')`), so mapping any of those 29 ids makes the gate exit
  with `unknown analyser rules`. `engine.review.diagnostics.coverage()` reports
  37 emitted rules with no diagnostic. Statuses are exactly `mapped`,
  `human_only`, `no_rule`; `human_only` entries may never be asserted offline.
- Known defect: `python tools/build_diagnostic_map.py` currently fails before
  writing. `MAPPED` maps `OUTLINE_ORDER` to `["paragraph_overlong",
  "para_drift"]`, but no enumerator produces `para_drift` (it exists only in
  `persona.py`/`kb.py`/`report.py` tables, not in `analysis.py` or
  `pedagogy.py`), so the gate exits with
  `unknown analyser rules: ['para_drift']`. The checked-in
  `knowledge/diagnostic_map.json` therefore predates that mapping and still maps
  `OUTLINE_ORDER` to `paragraph_overlong` alone. `MAPPED` also re-declares
  `INTRO_HOOK` and `THESIS_CLAIM`, so Python keeps only the later literal.
  Nothing in the test suite runs this gate.
- `validate_kb` contract: required keys `persona`, `moves`, `anti_ai_rules`,
  `endnote_template`, `banned_phrases`; at least 8 anti-AI rules; unique move
  ids; 4–6 patterns per move; `required_slots` must equal the slots actually
  used and every pattern must format with mock values; 2–3 endnote sections and
  a `"Dear "` opener; the extended KB needs >50 diagnostics, unique ids, a
  `verified_issue_flag` trigger, `when_unverified: do_not_emit`, evidence
  required, and source URLs that are `None` or begin with
  `https://knowledge.thinkingstorm.com/`; the legacy file must have exactly
  five keys and 12–16 moves.
- `mine_voice_corpus` exits when the folder has no `.docx`; the `voice_profile`
  keys it emits (`comment_words`, `sentence_lengths`, `sentences_per_comment`,
  rates, `top_labels`, `examples`) are the shape `export_astra_brief` reads, so
  the two must change together.
- `export_astra_brief` reads both corpus JSON files unguarded — it fails unless
  `mine_voice_corpus` has run first.
- `index_local_review_examples` is read-only against its source corpus, raises
  `ValueError` when no anchored comment is found, and imports
  `portal.feedback_extract`, so `tools/` no longer depends on `portal/` in one
  direction only.
- Local runtimes are loopback-only and one port each: Ollama
  `127.0.0.1:11434`, text llama-server `11435`, Strata `11436`, feedback
  humanizer `11437`. `setup_local_reviewer` also pins `OLLAMA_NO_CLOUD=1`,
  `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1` and installs the model
  into `output/local-model/models`.
- `setup_local_reviewer` verifies the Ollama archive SHA-256
  (`bda4a493…7eda12a`) before extracting, and `start_strata_reviewer` refuses
  to start a duplicate server when the port already serves another model.
- `deploy_local_reviewer` validates recorded PIDs against the expected command
  lines (`run_portal.py`, `engine.review.cli watch … inbox`) before stopping
  them, archives the previous `output/review-runtime.json` into the deployment
  directory, writes the new profile atomically (`.new` + `Move-Item`), refuses to
  continue while port 8000 is still held, and health-checks `/thinkingstorm`
  before recording the deployment. The deployed watcher runs `--interval 10` (the
  orchestrator's poller uses 30).
- Feedback-humanizer config contract (`engine/feedback_humanizer.py`, enforced
  when `LocalHumanizer` is constructed): only the keys `base_url`, `model`,
  `model_name`, `prompt_path`, `budget_seconds`, `call_timeout_seconds`,
  `provider`; `base_url` must be loopback `http` with no path, query,
  credentials or fragment; `provider` is `completion` or `instruct` and the
  alias must be `thinkingstorm-humanizer` or `thinkingstorm-editor`
  respectively; `prompt_path` must be absolute; the completion prompt must hash
  to the pinned `PROMPT_FINGERPRINT`; `budget_seconds` ≤ 180 and
  `call_timeout_seconds` ≤ 30. A session takes an exclusive lock on
  `output/humanizer/review.lock`, verifies `/v1/models` serves the configured
  alias and `/slots` is idle, rejects a passage over 6000 bytes, and raises
  `TruncatedRewrite` rather than returning a cut-off rewrite.
- `humanize_saved_review.py` never overwrites the source manuscript, requires
  `payload['fingerprint']` to equal the reloaded manuscript fingerprint, deletes
  the new `.docx` when `validate_deliverable` fails, and records the result in a
  sibling `.review.json` written with `path.with_suffix('.review.json')`. It
  always uses reviewer initials `RB` and needs a live humanizer runtime; there is
  no fallback path.
- Review writes stay outside the source: local reviews land in
  `output/local-model/reviews/inputs/`, audit artifacts outside the corpus, and
  humanized deliverables wherever `--output` points.

## Side Effects

- Disk writes: `style_corpus/{voice_corpus,voice_profile,exemplars,exemplar_stats}.json`;
  `docs/VOICE_PROFILE.md`, `docs/ASTRA_BRIEF.md`; `knowledge/diagnostic_map.json`;
  `output/local-model/` (`config.json`, `candidate-config.json`, `examples.json`,
  `TextReviewer.Modelfile`, `ollama.pid`, `reviewer.pid`, `strata-server.pid`,
  `strata-runtime.private.json`, `strata-original-config.private.json`, logs,
  `strata-traces/`, `strata-data/`, `latest-deployment.txt`, `models/`,
  `reviews/`, `deployments/`);
  `output/humanizer/` (`config.json`, `server.pid`, `server.stdout.log`,
  `server.stderr.log`, `review.lock`, `llamacpp/`, downloaded weights);
  `output/deployments/<stamp>-local-reviewer/` (+ stdout/stderr logs,
  `deployment.json`, `previous-runtime.json`); `output/review-runtime.json`;
  `output/daemon_pids.json` (rewritten `ServerPID`/`WatcherPID`);
  `scratch/corpus-audit/{audit.json,comparison.html}`; sibling
  `<name>.review.json` sidecars next to every written deliverable.
- Subprocesses: `ollama.exe show/create/pull/stop`, `llama-server.exe` (text
  reviewer and humanizer), Strata `.venv\Scripts\python.exe serve\server.py`,
  `python run_portal.py`, `python -m engine.review.cli watch --inbox … --outbox
  … --interval 10 --backend …`, `python tools/create_text_reviewer.py`,
  `python tools/index_local_review_examples.py`, `curl.exe` (pinned downloads)
  and `Expand-Archive`.
- Network: loopback model runtimes only at review time, except
  `setup_local_reviewer.ps1` / `setup_feedback_humanizer.ps1`, which fetch from
  `github.com` (Ollama, llama.cpp, CUDA runtime) and
  `registry.ollama.ai`/`ollama pull` for weights — every download
  checksum-verified before use; `llama-server` itself runs with `--offline`.
- Reads outside the repository: `C:\Users\shashank\Downloads\Doc examples`,
  `%USERPROFILE%\Strata`, and hardcoded exemplar paths in
  `build_style_corpus`/`export_astra_brief`/`endnote_extract`/
  `setup_local_reviewer` defaults. Those paths are machine-specific.
- Mutates no manuscript: `strip_comments` copies, `run_local_review` /
  `audit_review_corpus` write cleaned inputs into `inputs/` directories under
  `output/` or `scratch/`, and `humanize_saved_review` writes a new deliverable
  — never over the source `.docx`.

## Verification

- Run: `python -m unittest discover -s tests` (green; 100 tests at the time of
  writing).
- Directly covered by the suite: `validate_kb` (`tests/test_kb.py`),
  `body_letter` (`tests/test_endnote_extract.py`), `extract`
  (`tests/test_review_pipeline.py`), `audit`
  (`tests/test_native_ooxml.py`, `tests/test_local_review.py`). The humanizer
  engine side is covered by `tests/test_feedback_humanizer.py`.
- Not covered: `humanize_saved_review.py`, the provisioning/deploy PowerShell
  scripts, the corpus miners, `build_diagnostic_map`, `report_diagnostic_coverage`
  and `audit_review_corpus`.
- Manual gates: `python tools/validate_kb.py`,
  `python tools/report_diagnostic_coverage.py`,
  `python tools/build_diagnostic_map.py` (currently exits non-zero on its stale
  `para_drift` mapping — see Invariants),
  `python tools/audit_native.py <deliverable.docx>`, and
  `python tools/audit_review_corpus.py <folder> --out scratch/corpus-audit`.
- Manual humanizer smoke test:

  ```powershell
  tools/setup_feedback_humanizer.ps1
  tools/start_feedback_humanizer.ps1
  python tools/humanize_saved_review.py <review.json> --output output/<name>_humanized.docx
  ```

  Then inspect the sibling `.review.json`: `generation.humanization` records the
  attempted/rewritten/retained counts and `review_quality.warnings` names any
  passage the guards kept verbatim.
