# Apex Academic Review Engine Blueprint

## System Overview

A single-host Python application comprising two primary subsystems: a FastAPI
portal (`portal/`) that accepts student manuscripts, and a deterministic review
engine (`engine/review/`) that turns each manuscript into a Word deliverable —
native margin comments, a native endnote letter, and an in-place tracked-change
copy ("redline") — without rewriting the student's prose. The `rules` review
engine is offline and model-free by default; the portal acts as an HTTP workflow
layer over it, providing SQLite state, commercial and administrative surfaces,
and the Reviewer Studio workbench (`/thinkingstorm`). Historically, internal
routes, environment variables (`TS_*`), and knowledge-base (KB) files retain the
`TS` / `thinkingstorm` namespace.

The repository also carries operational packages (host supervisor, browser
consulting bridge, outbound campaigns, payments, compliance constants, corpus
miners, and KB utilities). Most of these sit outside the review judgment path,
but `portal.server` imports `payments.stripe_gateway`,
`payments.institutional_invoicing`, `security.auth`, `security.pii_scrubber`,
`security.audit_logger`, `mail.smtp_server`, and
`engine.self_prompting_framework` for its commercial and administrative routes.
Importing `portal.server` therefore executes their module-level initialization
(creating `output/` and `orchestrator/` directories and initializing tables in
`orchestrator/desk_jobs.db` and `security/users.db`) and mounts those routes in
the same FastAPI application that serves `/submit`.

## Problem & Scope

- Apex turns a student `.docx` manuscript into a shippable review package: native
  margin comments anchored to exact quoted words (bound via OpenXML
  `w:commentRangeStart` / `w:commentRangeEnd` markers), one KB hyperlink per
  labeled comment, a native endnote letter in `word/endnotes.xml`, and an
  in-place redline copy of the body (`engine/review/trackchanges.py`).
- The engine must work without a model provider (`backend="rules"`), so the same
  draft yields identical findings, comments, and ordering on any host.
- The portal owns intake (`/submit`), personally identifiable information (PII)
  redaction, the reviewer queue (`submit` -> `claim` -> `approve`), delivery,
  and commercial surfaces; it delegates release-gated review judgment to
  `engine/review/`.
- Scope stops at editorial diagnosis of supplied text: the system never
  ghostwrites student prose, and `vendor/` (`vendor/elephant-goldfish-model` and
  `vendor/humanizer`) is excluded third-party material outside this contract set.
- Operational packages (tunnel supervision, browser bridge, outbound campaigns,
  payments, and SMTP) are explicit system boundaries in this contract, not part
  of the review runtime.

## Goals & Non-Goals

- Goal: fail closed. `engine/review/validate.py` reopens the generated `.docx`
  archive and refuses to ship any package whose paragraph text or comment anchor
  set drifted from the source model.
- Goal: keep review decisions auditable — each comment carries a rule ID, an
  exact student quote, and a diagnostic name, and every run writes a `.review.json`
  sidecar beside the delivered `.docx`.
- Goal: keep the `rules` path deterministic and offline, with loopback or cloud
  model execution reachable only through explicit host-level opt-ins.
- Non-goal: a hosted multi-tenant service. Persistent state lives in three
  local SQLite files (`orchestrator/desk_jobs.db`, `security/users.db`, and
  `orchestrator/orchestrator.db`), and generated artifacts are files under
  `output/` and `outbox/`.
- Non-goal: rewriting student prose. The v2 pipeline (`engine/review/`) applies
  deterministic anti-AI pattern scrubbing (`engine/review/anti_ai_patterns.py`)
  only to reviewer feedback prose; the optional loopback feedback rewriter
  (`engine/feedback_humanizer.py`, `LocalHumanizer`) is guarded by
  `engine/review/humanization.py`; and the legacy compatibility module
  (`engine/anti_ai_humanizer.py`, whose rewrite helpers are non-mutating no-ops)
  is excluded from the release-gated path.
- Non-goal: Redis/Celery-style distributed queues, schedulers, or caches. Review
  work runs synchronously in the HTTP request or in the filesystem drop watcher
  (`python -m engine.review.cli watch`), while `run_poller.py` runs periodic
  SQLite telemetry and model-quota heartbeats.

## Alternatives Considered

- Per-package SQLite stores instead of one shared `orchestrator/desk_jobs.db`:
  rejected because `/submit`, `/reviewer/claim`, `/reviewer/approve`, mail
  spooling, institutional invoicing, and outbound campaign scripts join across
  `submissions`, `crm_leads`, and `reviewer_earnings`. Splitting the file would
  require `ATTACH` cross-database queries or data duplication across a
  single-host deployment.
- A managed relational database: rejected for a single-host deployment to avoid
  running a database server or migration framework.
- A model-only reviewer: rejected because exact span anchoring, the OpenXML
  release gate, and deterministic outputs must work on an air-gapped host; rules
  remain the default and model backends stay opt-in.
- Deleting the earlier review builders instead of retaining three generations
  (Generation 1: current v2 `engine/review/` via `review_document`; Generation 2:
  portal report builder in `engine/processor.py` `ReviewProcessor`,
  `engine/deep_pipeline.py` `DeepReviewPipeline`, `engine/prompts.py`, and
  `engine/cli.py`; Generation 3: legacy comment/endnote and tracked-change
  generators in `engine/thinkingstorm_engine.py`,
  `engine/word_native_comments.py`, `engine/openxml_track_changes.py`, and
  `engine/anti_ai_humanizer.py`): deferred because the portal's Reviewer Studio
  manual path and several tests still import `thinkingstorm_engine` and
  `ReviewProcessor`. The exit condition is migrating all portal routes and tests
  to `engine/review/`.
- Rebuilding uploaded `.docx` files from extracted plain text: rejected because
  it strips images, tables, fonts, and styles; the portal copies lowercase
  `.docx` uploads byte-for-byte instead.

## Risks & Mitigations

- **SQLite lock contention**: Multiple OS processes (uvicorn workers,
  `run_poller.py`, `scripts/run_smtp.py`, and `outbound/` scripts) access
  `orchestrator/desk_jobs.db` without WAL mode or a busy timeout (see Global
  Invariants), which can raise `sqlite3.OperationalError: database is locked`.
  Mitigation is operational serialization of batch scripts and per-job artifact
  filenames (`<job_id>_*`), not a transactional queue.
- **Unbacked SQLite state and ad-hoc schema evolution**: No automated backup,
  retention, or migration runner exists for `orchestrator/desk_jobs.db`,
  `security/users.db`, or `orchestrator/orchestrator.db` (all git-ignored via
  `*.db`). Mitigation is external file-level backup; schema changes rely on
  `CREATE TABLE IF NOT EXISTS` and require manual `ALTER TABLE` scripts when
  columns change.
- **Unintended model activation and single-flight humanizer lock**: Because
  `engine.review_runtime.apply_runtime_defaults()` reads
  `output/review-runtime.json` (or `TS_RUNTIME_PROFILE`) and checks for
  `output/local-model/config.json` (see Global Invariants), leftover profile
  files in `output/` can switch the default `rules` path to `local` or enable
  `LocalHumanizer` without shell environment flags. In addition,
  `LocalHumanizer.session()` acquires a non-blocking exclusive OS lock on
  `output/humanizer/review.lock` (`budget_seconds <= 180`,
  `call_timeout_seconds <= 30`), so concurrent humanized review requests fail
  closed immediately (`HumanizerUnavailable` -> `PipelineError`) while a session
  is active. Mitigation is keeping `output/review-runtime.json` and
  `output/local-model/config.json` absent on air-gapped hosts.
- **Soft coverage thresholds in the release gate**: `engine/review/validate.py`
  fails closed on structural, anchor, word-count, and banned-phrase violations,
  whereas page-coverage and comment-density shortfalls record warnings and set
  `status: needs_review`. Mitigation is human reviewer inspection in Reviewer
  Studio plus `python -m engine.review.cli audit`.
- **Unredacted `.docx` deliverables, un-restored text/PDF PII tokens, and
  ungated certificates**: As detailed in Global Invariants, lowercase `.docx`
  uploads bypass PII scrubbing in the Word deliverable, text/PDF deliverables
  keep placeholder tokens after `/reviewer/approve/{job_id}`, Reviewer Studio
  (`/api/thinkingstorm/execute`) never runs PII scrubbing, and
  `/certificate/{job_id}` does not verify approval status. There is currently no
  runtime mitigation; operators must treat `.docx` deliverables in `output/` as
  containing raw student PII.

## Local Interface & Invariants

### Root Entrypoints

Only two Python launcher scripts reside directly in the repository root (direct
source, no package):

- [`run_portal.py`](./run_portal.py) — At module import time, inserts the
  repository root into `sys.path`, sets `os.environ["PYTHONPATH"]` to the
  repository root and `os.environ["PYTHONIOENCODING"] = "utf-8"`, and calls
  `engine.review_runtime.apply_runtime_defaults()` (which reads
  `TS_RUNTIME_PROFILE` or `output/review-runtime.json` to `setdefault`
  `TS_REVIEW_BACKEND`, `TS_HUMANIZER`, and `TS_HUMANIZER_CONFIG`, falls back to
  `TS_REVIEW_BACKEND="local"` if `output/local-model/config.json` exists, and
  raises `RuntimeError` if a profile file is invalid). Under
  `if __name__ == "__main__":`, starts `uvicorn.run("portal.server:app",
  host="127.0.0.1", port=8000, log_level="info")`.
- [`run_poller.py`](./run_poller.py) — At module import time, sets `PYTHONPATH`
  and `PYTHONIOENCODING="utf-8"`, updates `sys.path`, and imports
  `orchestrator.poller_daemon.run_poller_daemon` (which creates `output/` on
  import). Under `if __name__ == "__main__":`, parses an optional integer poll
  interval from `sys.argv[1]` (default `30` seconds) and runs
  `run_poller_daemon(interval)`, which executes read-only telemetry queries on
  `orchestrator/desk_jobs.db`, refreshes model cooldowns in
  `orchestrator/orchestrator.db` via `TokenManager`, seeds
  `outbound/leads_crm.csv` if absent via `LeadManager()`, and writes
  `output/daemon_heartbeat.json`.

All other operational daemon, watcher, tunnel, and SMTP launchers reside in
[`scripts/`](./scripts/EGM.md) and [`tools/`](./tools/EGM.md).

### Root Invariants

- Neither root launcher performs review analysis directly; each configures the
  process environment and delegates to `portal.server` or
  `orchestrator.poller_daemon`.
- Importing `run_portal` or `run_poller` does not start a network server or
  polling loop (`uvicorn.run` and `run_poller_daemon` are guarded by
  `if __name__ == "__main__":`), but importing `run_portal` mutates `sys.path`
  and `os.environ` and executes `apply_runtime_defaults()`, which raises
  `RuntimeError` if `output/review-runtime.json` is malformed.
- Root launcher scripts must never be imported by `engine/` or `tests/`.

## Subdirectories & System Boundaries

- [bridge](./bridge/EGM.md) — Chrome DevTools Protocol (CDP) Playwright bridge
  to authenticated ChatGPT and Qwen browser sessions for human-in-the-loop
  strategy consultations (`bridge/FRONTIER_SUPERVISOR_CONSULTATION.md`); never a
  runtime dependency of the review engine.
- [docs](./docs/EGM.md) — Development-only Elephant-Goldfish Model (EGM)
  workflow guide (`docs/EGM.md`), architecture and pipeline guides
  (`docs/THINKINGSTORM_PIPELINE.md`, `docs/LOCAL_THINKINGSTORM_REVIEWER.md`,
  `docs/FEEDBACK_HUMANIZER.md`), and feature specifications (`docs/designs/`).
- [engine](./engine/EGM.md) — Review engine package root housing three builder
  generations: Generation 1 in [engine/review](./engine/review/EGM.md) (the v2
  deterministic pipeline via `review_document`), Generation 2 (`engine/processor.py`
  `ReviewProcessor`, `engine/deep_pipeline.py` `DeepReviewPipeline`,
  `engine/prompts.py`, and `engine/cli.py`), and Generation 3
  (`engine/thinkingstorm_engine.py`, `engine/word_native_comments.py`,
  `engine/openxml_track_changes.py`, and compatibility no-op
  `engine/anti_ai_humanizer.py`), plus `engine/feedback_humanizer.py`
  (`LocalHumanizer`), `engine/review_runtime.py`, and
  `engine/self_prompting_framework.py`.
- [legal](./legal/EGM.md) — Verbatim compliance text constants for the
  Independent Educational Consultants Association (IECA), Family Educational
  Rights and Privacy Act (FERPA), and Service Level Agreement (SLA) surfaces.
- [mail](./mail/EGM.md) — Loopback RFC 5321 SMTP sink (`mail/smtp_server.py`,
  `ApexSMTPServer`) persisting inbound messages into `mail_spool` in
  `orchestrator/desk_jobs.db`.
- [orchestrator](./orchestrator/EGM.md) — Host service supervisor
  (`apex_service_monitor.py`, probing HTTP `:8000`, `cloudflared`, and
  `poller_daemon` every 15 seconds and writing `output/service_status.json`),
  read-only SQLite telemetry and heartbeat daemon (`poller_daemon.py`, writing
  `output/daemon_heartbeat.json`), and model quota registry (`token_manager.py`,
  backed by `orchestrator/orchestrator.db`).
- [outbound](./outbound/EGM.md) — B2B lead CSV/CRM ingestion, campaign dispatch,
  and conversion booking scripts writing to `orchestrator/desk_jobs.db`.
- [payments](./payments/EGM.md) — Stripe checkout tier catalog
  (`stripe_gateway.py`) and institutional purchase-order invoicing
  (`institutional_invoicing.py`).
- [plugins/dsh-egm-skills](./plugins/dsh-egm-skills/EGM.md) — Static plugin
  bundle registering the seven EGM skills and Goldfish reviewer personas;
  content-only, with no runtime code or model calls.
- [portal](./portal/EGM.md) — FastAPI application (`portal/server.py`), intake
  and reviewer routes, Reviewer Studio backend (`thinkingstorm_view.py`,
  `feedback_editor.py`, `feedback_extract.py`, `review_progress.py`), and UI
  helpers (`ui.py`, `directory_view.py`); [portal/static](./portal/static/EGM.md)
  holds the Reviewer Studio browser scripts and stylesheets.
- [scripts](./scripts/EGM.md) — Operational PowerShell and Python launchers
  (`start_server_daemon.ps1`, `stop_server_daemon.ps1`, `start_apex_monitor.ps1`,
  `launch_tunnel.ps1`, `start_ts_watcher.ps1`, `stop_ts_watcher.ps1`, and
  `run_smtp.py`) plus the Windows-to-macOS Git-bundle sync utility
  (`sync_to_mac.py`, writing `edtech_review_engine.bundle` at the repository root
  and `output/edtech_review_engine.bundle`); see `scripts/EGM.md` for PID/log
  paths and daemon-stop caveats.
- [security](./security/EGM.md) — Role-based user authentication (`auth.py`,
  backed by `security/users.db`), regex PII de-identification (`pii_scrubber.py`),
  and SHA-256 compliance audit logging (`audit_logger.py`).
- [tools](./tools/EGM.md) — Corpus mining (`mine_voice_corpus.py`), diagnostic
  map and KB validation (`build_diagnostic_map.py`, `validate_kb.py`), corpus
  replay (`audit_review_corpus.py`), and loopback model server provisioning and
  startup scripts (`setup_local_reviewer.ps1`, `start_local_reviewer.ps1`,
  `start_strata_reviewer.ps1`, `setup_feedback_humanizer.ps1`,
  `start_feedback_humanizer.ps1`, `deploy_local_reviewer.ps1`).

### Runtime Data & Non-Package Directories

- `knowledge/` — Read-only JSON inputs for `engine/review/`:
  `review_quality_profile.json` (required at import time by
  `engine/review/coverage.py`), `thinkingstorm_kb_v2.json` (loaded and cached at
  import time via `engine/review/persona.py` -> `kb.py`), `diagnostic_map.json`
  (cached on demand by `engine/review/diagnostics.py`), and legacy
  `thinkingstorm_kb.json` (checked by `tools/validate_kb.py`).
- `samples/` — Static archive `Apex_Institutional_Counselor_Sample_Pack.zip`
  resolved via `PROJECT_ROOT / "samples"` and served by
  `GET /samples/institutional-pack.zip` (returns HTTP 404 when absent).
- `style_corpus/` — Stylometric reference artifacts: `voice_corpus.json` (read by
  `GET /api/voice/baseline` via CWD-relative `Path("style_corpus/voice_corpus.json")`
  to return reference tutor sentence-length and burstiness metrics; 404s when
  absent), plus `voice_profile.json`, `exemplars.json`, and
  `exemplar_stats.json` generated and consumed by `tools/`.
- `inbox/`, `outbox/`, and `output/` — Working directories for the CLI drop
  watcher (`inbox/` -> `outbox/`, tracking state in `outbox/processed.json`) and
  portal/CLI review deliverables, runtime profiles, and logs (`output/`,
  git-ignored).
- `tests/` — `unittest` test suite and regression corpora under `tests/fixtures/`
  (protected by `AGENTS.md`: never regenerate fixture `.docx` files or corpus
  snapshots unless a schema change requires it).

## Global Invariants

- **Deterministic offline default and three explicit model opt-ins**: The default
  review path (`engine/review/` with `backend="rules"`) behind `/submit`,
  `/api/thinkingstorm/execute`, and `engine.review.cli` is 100% offline and
  deterministic (seeded via `sha1(fingerprint | rule | pos)`), making zero
  network or LLM calls. Three independent opt-ins alter that behavior:
  1. `TS_REVIEW_BACKEND=local` makes `review_document` query a loopback model
     configured in `output/local-model/config.json` (only loopback hosts in
     `{ollama, strata, llamacpp}` are permitted).
  2. `TS_HUMANIZER=local` (optionally paired with `TS_HUMANIZER_CONFIG`) injects
     `engine.feedback_humanizer.LocalHumanizer`, which rewrites composed comment
     and endnote prose through a loopback server on `127.0.0.1:11437` under
     `engine/review/humanization.py` fact-masking guards and acquires a
     non-blocking exclusive lock on `output/humanizer/review.lock`
     (`budget_seconds <= 180`, `call_timeout_seconds <= 30`, failing closed with
     `HumanizerUnavailable` if busy).
  3. `APEX_ENABLE_LLM=1` plus `OPENAI_API_KEY` enables OpenAI chat completions
     exclusively in Generation 2's `engine.processor.ReviewProcessor` class
     (never in `engine/review/`).
  Both `run_portal.py` (at import time) and `engine.review.cli.main()` invoke
  `engine.review_runtime.apply_runtime_defaults()`, which seeds
  `TS_REVIEW_BACKEND`, `TS_HUMANIZER`, and `TS_HUMANIZER_CONFIG` from
  `TS_RUNTIME_PROFILE` or `output/review-runtime.json` (or sets
  `TS_REVIEW_BACKEND="local"` when `output/local-model/config.json` exists). Air-gapped
  deployments must ensure neither config file is present under `output/`.
- **Manuscript preservation**: Student body text is never rewritten by the v2
  pipeline. Margin comments (`word/comments.xml`) and endnote letters
  (`word/endnotes.xml`) are native OpenXML parts, redlines edit
  `word/document.xml` runs in place, quoted student spans are masked during
  anti-AI scrubbing (`engine/review/anti_ai_patterns.py`), and
  `engine/review/validate.py` fails closed if any paragraph text or anchor drifts.
- **Upload byte preservation and `.DOCX` case-sensitivity defect**: On `/submit`,
  the portal copies uploaded `.docx` bytes directly to `output/<job_id>_raw.docx`
  when `file.filename.endswith(".docx")`. Known defect: because that suffix check
  is case-sensitive, an uppercase `.DOCX` upload falls through to the plain-text
  rebuild branch (`Document()` from `sanitized_text`), losing original OpenXML
  formatting and embedding placeholder tokens.
- **Three SQLite databases with default file locking**:
  1. `orchestrator/desk_jobs.db` backs `portal`, `mail`, `outbound`, `payments`,
     `security.audit_logger`, and `engine.self_prompting_framework`.
  2. `security/users.db` backs `security.auth`.
  3. `orchestrator/orchestrator.db` backs `orchestrator.token_manager.TokenManager`.
  All three are excluded by `*.db` in `.gitignore`, and every module opens
  per-call `sqlite3.connect(...)` handles without enabling WAL mode or setting a
  busy timeout.
- **PII lifecycle and known redaction gaps**: In the portal workflow (`submit`
  -> reviewer `claim` -> reviewer `approve`), `/submit` runs
  `security.pii_scrubber.PIIScrubber.deidentify()` on extracted text and stores
  both raw `original_text` and `pii_token_map` in `submissions`. However:
  1. Lowercase `.docx` uploads are written to `<job_id>_raw.docx` from raw
     uploaded bytes, so `.docx` deliverables retain unredacted student PII.
  2. Non-`.docx` (text/PDF) and uppercase `.DOCX` inputs build `<job_id>_raw.docx`
     from `sanitized_text`, and `/reviewer/approve/{job_id}` never calls
     `PIIScrubber.reidentify()`, so their certified `.docx` deliverables retain
     placeholder tokens (`[APPLICANT_NAME]`, `[APPLICANT_<PART>]`, `[EMAIL_<n>]`,
     `[PHONE_<n>]`, `[SECONDARY_SCHOOL_<n>]`).
  3. Reviewer Studio (`/api/thinkingstorm/execute`) never invokes `PIIScrubber`.
  4. `GET /certificate/{job_id}` issues the compliance HTML certificate without
     verifying that the submission has been approved.
- **Compliance and marketing constants**: Public compliance claims and security
  headers are governed by [`legal/`](./legal/EGM.md) and
  [`security/`](./security/EGM.md); documented code-vs-claim divergences in those
  contracts remain until fixed in code.
- **Third-party exclusion**: `vendor/` is third-party material; do not document,
  edit, or test it as project code.

## Global Side Effects

- **Filesystem writes**: Writes review deliverables (`.docx`), sidecars
  (`.review.json`), runtime profiles, PID files, and logs to `output/` and
  `outbox/`; writes SQLite databases to `orchestrator/desk_jobs.db`,
  `orchestrator/orchestrator.db`, and `security/users.db`; writes the humanizer
  lockfile to `output/humanizer/review.lock`; and writes
  `edtech_review_engine.bundle` (at root and `output/`) when
  `scripts/sync_to_mac.py` runs.
- **Long-lived processes and loopback ports**: Spawns background processes only
  through explicit launchers in root, `scripts/`, and `tools/`:
  - `127.0.0.1:8000` — FastAPI portal (`run_portal.py`).
  - `127.0.0.1:1025` — Loopback SMTP sink (`scripts/run_smtp.py`).
  - `127.0.0.1:11434` — Local Ollama daemon (`tools/setup_local_reviewer.ps1`).
  - `127.0.0.1:11435` — Local reviewer `llama-server` (`tools/start_local_reviewer.ps1`).
  - `127.0.0.1:11436` — Strata reviewer `llama-server` (`tools/start_strata_reviewer.ps1`).
  - `127.0.0.1:11437` — Feedback humanizer `llama-server` (`tools/start_feedback_humanizer.ps1`).
  - Detached workers without listening ports: `run_poller.py`,
    `orchestrator/apex_service_monitor.py`, `cloudflared tunnel`, and
    `python -m engine.review.cli watch`.
- **External network boundaries**: Outbound SMTP campaign dispatch (`outbound/`),
  Stripe API calls (`payments/`), and Playwright CDP automation (`bridge/`) are
  isolated to their respective packages and are never triggered by
  `engine/review/` or the unit test suite.
- **Import-time side effects**: Several modules mutate the filesystem, SQLite
  databases, or processes on `import`:
  - `run_portal.py` and `run_poller.py` mutate `sys.path` and `os.environ`
    (`run_portal.py` also runs `apply_runtime_defaults()`).
  - `portal.server` creates `output/` and `orchestrator/`, runs `init_db()` and
    `init_compliance_schema()`, and instantiates `SelfPromptingFramework()`,
    which creates `self_prompt_registry` and `self_prompt_runs` and seeds five
    prompt rows in `orchestrator/desk_jobs.db`.
  - `payments.institutional_invoicing` runs `init_invoicing_db()` (creating
    `institutional_invoices` in `orchestrator/desk_jobs.db`).
  - `security.auth` runs `init_user_db()` (creating and seeding `security/users.db`),
    and `security.audit_logger` runs `init_compliance_schema()` on
    `orchestrator/desk_jobs.db`.
  - `orchestrator.poller_daemon` and `orchestrator.apex_service_monitor` create
    `output/` on import; `orchestrator/check_db.py` and several operational
    scripts in `bridge/`, `outbound/`, and `tools/` lack `__main__` guards and
    create directories, query/mutate `desk_jobs.db`, or launch Playwright/CLI
    workflows on import (see their child `EGM.md` contracts) and must never be
    imported by runtime or test modules.

## System Verification

- **Full test suite**: `python -m unittest discover -s tests` (100 tests across
  the review pipeline, anti-AI pattern scrubber, deliverable OpenXML integrity,
  humanizer guards, KB v2 schema, and Reviewer Studio UI).
- **CLI release-gate selftest**:
  `python -m engine.review.cli selftest --fixtures tests/fixtures`
- **Studio JavaScript syntax check**: `tests/test_studio_js.py` runs
  `node --check` against the rendered Reviewer Studio script.
- **Database side effects during testing**: The test suite is not
  database-isolated; test modules that import `portal.server` trigger
  `init_db()`, `init_compliance_schema()`, `init_invoicing_db()`,
  `init_user_db()`, and `SelfPromptingFramework.__init__()`, creating or
  updating `orchestrator/desk_jobs.db` and `security/users.db`. Operational
  packages (`bridge`, `orchestrator`, `outbound`, `scripts`) have no dedicated
  `unittest` modules; see their respective `EGM.md` contracts for verification
  commands.
