# Portal (FastAPI Review Desk Server)

## Overview

The HTTP front end of the review engine. `portal/server.py` is a single FastAPI
application (`title="Apex Academic Review Desk"`, `version="3.5.0"`) that serves
every page and API of the product: the public intake form, the ThinkingStorm
Studio, the reviewer workbench, client job status, downloads, and the
admin/commercial dashboards. Around it sit six helper modules that keep the
route module from growing further:

| Module | Role |
| --- | --- |
| `server.py` | The whole FastAPI app: routes, upload handling, review hand-off, persistence, downloads. |
| `directory_view.py` | `render_directory_page(request)` — one static HTML page (Platform Capability Directory) shared by three routes. |
| `thinkingstorm_view.py` | `get_thinkingstorm_studio_html(user)` — wraps `static/studio.html` in the shared shell and lists the four Studio scripts. |
| `ui.py` | `workspace_page(...)`, `icon(...)` and `ASSET_VERSION` — the workspace layout, navigation and asset version. |
| `feedback_extract.py` | `extract_original_feedback(data, filename)` — reads comments/endnote out of an uploaded DOCX. |
| `feedback_editor.py` | `register_review(...)` / `save_feedback(...)` / `FeedbackSaveError` / `MAX_BODY` — the capability-token feedback save path that rewrites `word/comments.xml` and `word/endnotes.xml` in place and re-runs the release gate. |
| `review_progress.py` | `ReviewProgressRegistry` and the module singleton `review_progress` — bounded, in-memory, thread-safe progress for one in-flight Studio review. |

Architecturally the portal is a **thin orchestrator over a review core**. All
review judgement is delegated to `engine.review.*`; the portal never scores a
document itself and adds no model call of its own. That core is deterministic and
offline on its default `rules` backend; the engine's optional `local` backend is
selected by `TS_REVIEW_BACKEND`, and the optional feedback rewriter by
`TS_HUMANIZER`, both outside this module. Persistence is a single SQLite file,
artefacts are files in `output/`, and both are created as import side effects.

Three request paths run or continue a review deliverable, and they must stay
behaviourally aligned:

1. **`POST /submit`** — the commercial intake path: PII scrubbing, rubric,
   redline, commented deliverable, rubric HTML, row in `submissions`.
2. **`POST /api/thinkingstorm/execute`** — the Studio path: same deterministic
   pipeline, plus optional reviewer-supplied comments/endnote, live progress,
   and a feedback-editing capability token.
3. **`POST /api/thinkingstorm/feedback/{job_id}`** — the Studio's save path:
   reviewer-edited comment bodies and endnote are written into the existing
   deliverable, re-validated, and published atomically.

## Problem & Scope

- The portal is the only HTTP surface: public intake, the ThinkingStorm Studio,
  the reviewer workbench, client status/downloads, certificates and the
  commercial/admin dashboards.
- It is a thin orchestrator: `engine.review.*` owns diagnosis and deliverable
  assembly, and the portal only materialises inputs, stores rows and serves
  files. The one optional rewrite stage is injected into the engine
  (`feedback_rewriter=`), never applied by the portal.
- Persistence is one SQLite file (`orchestrator/desk_jobs.db`) plus artefacts in
  `output/`; both are created as import side effects.
- Two long-running review entry points must stay aligned: commercial `/submit`
  (PII scrub, report and commented DOCX) and Studio
  `/api/thinkingstorm/execute` (same pipeline, optional reviewer
  comments/endnote, progress tracking).
- In scope: request parsing, capability checks, progress bookkeeping, and the
  SQLite/artefact bookkeeping around each review.

## Goals & Non-Goals

- Goal: keep the rules review path deterministic and offline, with no portal-side
  model call. The only model-backed component is the engine's injected
  humanizer, which is off unless `TS_HUMANIZER=local`.
- Goal: accept DOCX, PDF and plain text without damaging an uploaded DOCX; the
  original bytes are copied and only copies are edited.
- Goal: let a reviewer edit feedback in place after a review, with the downloaded
  DOCX always matching the last successfully validated save.
- Goal: persist enough state for claim/approve, earnings, compliance and client
  status, with a per-request SQLite connection.
- Non-goal: per-route authorization as a complete policy. Only seven handlers
  consult `get_current_user`; the rest are unauthenticated (see Invariants).
- Non-goal: background job processing in the web process; the poller and watcher
  are separate entrypoints. Progress lives in one process's memory only.
- Non-goal: re-identification of redacted PII at approval; the scrubber supports
  it, but the portal does not call it (known defect).

## Alternatives Considered

- A separate front-end service consuming a JSON API: rejected because every page is a
  server-rendered Python string and the Studio is the only rich client; splitting the
  UI would add a second deployment unit.
- Per-request database files or an ORM: rejected in favour of one `desk_jobs.db` with
  `sqlite3.Row` and `CREATE TABLE IF NOT EXISTS`, matching the poller, mail, invoicing
  and outbound scripts that already open that file.
- Building the deliverable from extracted text on every upload: rejected for DOCX
  because it drops images, tables and styles; the portal copies the bytes and lets the
  engine edit a copy.
- A model call in the portal for feedback or report text: rejected; `ReviewProcessor`
  and the engine's rules path are deterministic. The humanizer exists as a separate,
  opt-in transport (`engine/feedback_humanizer.py`) whose output only ever passes
  through the engine's preservation guards.
- Re-reviewing the manuscript to apply edited feedback: rejected; `save_feedback`
  rewrites only `word/comments.xml` and `word/endnotes.xml` and keeps
  `word/document.xml` byte-identical, so anchors and formatting cannot drift.
- Server-sent events or a websocket for progress: rejected in favour of a polling
  endpoint plus an in-memory registry, because the portal runs as one process and the
  review itself is a single blocking threadpool task.

## Risks & Mitigations

- Most routes are unauthenticated, including client status, certificates, downloads,
  `/api/health`, `/invoices/{id}`, both Studio JSON APIs and the feedback save API.
  Mitigation is code-level route gating; the current contract only documents the
  exposure.
- The feedback save API is reachable without a session; its protection is the
  per-review capability token (`edit_token`) plus the revision/hash checks in
  `feedback_editor.py`. Anyone who sees a token can edit that one review. Mitigation
  is treating the token like a secret and keeping the file-scoped validation.
- `/download/{filename}` is unauthenticated, so any client's artefact can be fetched
  by name. Path traversal is blocked (`'/'`, `'\\'`, `'.'`, `'..'`, and a resolved
  parent must equal `OUTPUT_DIR`), but there is no ownership check.
- Approval is repeatable and has no idempotency guard: each POST credits another 300
  INR and appends another delivery notification. Mitigation is a status check plus a
  unique earnings key on `(reviewer_email, job_id)`.
- `/submit` rebuilds the DOCX for uppercase extensions because its verbatim-copy check
  is case-sensitive. Mitigation is to use the already-computed lower-cased suffix.
- A misconfigured humanizer is a hard failure, not a silent downgrade: an invalid
  config raises `HumanizerUnavailable`, `feedback_rewriter()` turns it into HTTP 503,
  and an in-review failure becomes a `PipelineError` (HTTP 422 on both review paths).
  Mitigation is the pinned prompt fingerprint, the loopback-only origin check and the
  busy lock in `engine/feedback_humanizer.py`.
- SQLite is the only concurrency control, with no WAL or busy timeout; the web
  threadpool, poller, SMTP sink and outbound scripts can contend. Mitigation is
  operational serialisation and distinct `job_id` filenames.
- The progress registry is in-memory and per-process: a restart, a second worker or an
  eviction at capacity (256) makes a poll answer 404. Mitigation is that the review
  itself never depends on progress — `engine.review.progress.emit_progress` swallows
  observer errors.

## Interface

### Application object

- `app` — the FastAPI instance; `app.mount("/assets", StaticFiles(directory=PROJECT_ROOT/"portal"/"static"), name="workspace-assets")` serves `portal/static/` (see [./static/EGM.md](./static/EGM.md)).
- Module-level singletons: `processor` (`ReviewProcessor`), `track_engine`
  (`WordTrackChangesEngine(author="Apex Admissions Editorial Desk")`), `scrubber`
  (`PIIScrubber`), `gateway` (`StripeGateway`), `self_prompt_engine`
  (`SelfPromptingFramework`), and `review_progress` (`ReviewProgressRegistry()`).
- Module-level helpers: `feedback_rewriter()`, `normalize_extracted_text(raw)`,
  `get_db()`, `init_db()`, `get_service_telemetry()`, `run_sample_audit(text, institution)`,
  `_execute_thinkingstorm_pipeline(...)` and the `CLICHE_RULES` table used by the
  public sample audit.
- `feedback_rewriter()` (`server.py:57`) calls `engine.feedback_humanizer.configured_rewriter()`
  and converts any `RuntimeError` into `HTTPException(503)`. It returns `None` when
  `TS_HUMANIZER` is unset/`off`, and a `LocalHumanizer` when it is `local`.
- Constants: `PROJECT_ROOT`, `OUTPUT_DIR` (`<repo>/output`), `DB_PATH`
  (`<repo>/orchestrator/desk_jobs.db`), `STATUS_FILE`
  (`output/service_status.json`).

### Routes

Almost every page is an HTML string built in Python (Tailwind — and Alpine on the
directory page — from CDNs), except the Studio, which uses the local workspace
shell from `ui.py`.

| Method | Path | Handler | Purpose |
| --- | --- | --- | --- |
| GET | `/` | `landing_page` | Public intake/conversion page; personalises nav for a signed-in user. |
| POST | `/api/audit/sample` | `audit_sample_endpoint` | JSON cliché/voice sample audit, no persistence. |
| GET/POST | `/login` | `login_page`, `process_login` | Session cookie `apex_session` (httponly, 7d) and role-based redirect. |
| GET | `/logout` | `process_logout` | Clears the session cookie. |
| GET/POST | `/reviewer/join` | `reviewer_join_page`, `process_reviewer_join` | Reviewer signup (role `reviewer`). |
| GET/POST | `/reviewer/qualify` | `reviewer_qualify_page`, `process_reviewer_qualify` | 3-question exam; ≥2 correct (`B`) required. |
| POST | `/submit` | `submit_manuscript` | Commercial intake path (see below). |
| GET | `/status/{job_id}` | `status_redirect` | 303 to the client status page. |
| GET | `/client/status/{job_id}` | `client_status` | Client-facing status, score and download links. |
| GET | `/thinkingstorm` | `thinkingstorm_studio` | Studio page via `thinkingstorm_view`. |
| POST | `/api/thinkingstorm/original-feedback` | `thinkingstorm_original_feedback` | Read existing comments/endnote from a DOCX. |
| POST | `/api/thinkingstorm/execute` | `execute_thinkingstorm_pipeline` | Studio review path (see below); accepts optional `progress_id`. |
| POST | `/api/thinkingstorm/feedback/{job_id}` | `save_thinkingstorm_feedback` | Saves reviewer-edited feedback into the existing DOCX (JSON, capability token). |
| GET | `/api/thinkingstorm/progress/{progress_id}` | `thinkingstorm_progress` | Poll one review's progress snapshot (`Cache-Control: no-store`). |
| GET | `/reviewer` | `reviewer_workbench` | Queue + earnings; role `reviewer`/`admin` only. |
| POST | `/reviewer/claim/{job_id}` | `claim_job` | First-writer-wins claim; role-gated. |
| GET | `/reviewer/calibrate/{job_id}` | `calibrate_view` | Split-screen calibration; role-gated. |
| POST | `/reviewer/approve/{job_id}` | `approve_job` | Certify, hash, credit ₹300, append delivery log; role-gated. |
| POST | `/reviewer/payout/request` | `request_payout` | Marks that reviewer's pending earnings `paid`; role-gated. |
| GET | `/certificate/{job_id}` | `compliance_certificate` | Compliance certificate page. |
| GET | `/checkout/{package_id}` | `checkout_page` | Institutional package checkout page via `payments.stripe_gateway.PACKAGES`. |
| POST | `/checkout/process` | `process_checkout` | Processes the checkout and books the package. |
| GET | `/checkout/confirmation/{tx_id}` | `checkout_confirmation` | Checkout confirmation page. |
| GET | `/agency/dashboard` | `agency_dashboard` | Agency-side job list with download links. |
| GET | `/download/{filename}` | `download_file` | Serves one `OUTPUT_DIR` file by exact name (see below). |
| GET | `/download/commented/{job_id}` | `download_commented_docx` | Finds `<job_id>_*commented.docx` and strips the job prefix. |
| GET | `/download/docx/{job_id}` | `download_docx_by_job_id` | `submissions.docx_filename`, with a healing scan. |
| GET | `/download/report/{job_id}` | `download_report_by_job_id` | `submissions.html_filename`. |
| GET | `/samples/institutional-pack.zip` | `download_sample_pack` | Static sample pack from `samples/`. |
| GET | `/invoices/{invoice_id}` | `view_invoice_page` | One invoice via `payments.institutional_invoicing`. |
| POST | `/api/invoices/create` | `create_invoice_api` | Creates an institutional invoice. |
| GET | `/admin/invoices` | `institutional_invoices_dashboard` | Invoice dashboard. |
| POST | `/api/mail/send` | `send_mail_api` | Sends mail through `smtplib`. |
| GET | `/admin/mail` | `corporate_webmail_dashboard` | Spooled-mail inbox via `mail.smtp_server.get_spooled_mail`. |
| POST | `/api/inbound/lead-reply` | `inbound_lead_reply` | Updates `crm_leads` by email. |
| GET | `/legal/attestation` | `legal_attestation_page` | `legal.contracts` IECA text. |
| GET | `/legal/dpa` | `legal_dpa_page` | `legal.contracts` FERPA DPA text. |
| GET | `/admin` | `admin_dashboard` | Operations console. |
| GET | `/admin/services` | `service_monitor_dashboard` | Telemetry and host services. |
| GET | `/admin/crm` | `crm_dashboard` | CRM lead console. |
| GET | `/admin/remote` | `mobile_remote_console` | Mobile remote console. |
| GET | `/admin/company` | `company_governance_dashboard` | Company governance console. |
| GET | `/admin/self-prompting` | `self_prompting_dashboard` | Self-prompting console. |
| GET | `/admin/outreach` | `client_outreach_console` | Outbound outreach console. |
| POST | `/api/self-prompting/run` | `run_self_prompting_api` | Runs `engine.self_prompting_framework`. |
| GET | `/api/self-prompting/metrics` | `get_self_prompting_metrics_api` | Aggregate self-prompting metrics. |
| GET | `/api/self-prompting/registry` | `get_self_prompting_registry_api` | Current meta-prompt registry. |
| GET | `/admin/directory`, `/docs/capabilities`, `/admin/system-map` | `platform_capabilities_directory` | All three aliases return `render_directory_page(request)`; FastAPI's own `/docs` (Swagger) is untouched. |
| GET | `/api/voice/baseline` | `voice_baseline` | Sample of real reviewer prose from `style_corpus/voice_corpus.json`. |
| GET | `/api/health` | `health_check` | `{status, system, active_jobs, tracked_leads, reviewer_earnings_accrued_inr, …}`. |

### Upload handling

`POST /submit` accepts `student_name`, `email`, `mode` (default `admissions`),
`target_institution`, `counselor_brief`, `text` and an optional
`file: UploadFile`. Dispatch is by lower-cased suffix (`server.py:1391`):

| Suffix | Path | Failure mode |
| --- | --- | --- |
| `.docx` | `docx.Document(io.BytesIO(bytes))` → paragraph texts joined → `normalize_extracted_text` | any exception → HTML 400 "Could not parse document" |
| `.pdf` | `pypdf.PdfReader` → per-page `pdf_text_to_paragraphs` | same 400 |
| anything else | `bytes.decode("utf-8", errors="ignore")` → `plain_text_to_paragraphs` | same 400 |

With no file, the pasted `text` goes through `plain_text_to_paragraphs`. Empty
content after extraction is a 400 ("No text or document provided"). There is no
upload size cap on this route.

`POST /api/thinkingstorm/execute` is stricter and answers in JSON errors:

- `.docx` → also probes `extract_original_feedback`, then normalises paragraphs;
  unreadable DOCX → 400.
- `.pdf` → `pypdf` + `pdf_text_to_paragraphs`; fewer than 40 words → 400
  ("No selectable text was found in this PDF").
- `.txt`, `.md`, or no suffix → `plain_text_to_paragraphs` on the decoded bytes.
- `.doc` → 400 ("Legacy .doc files are not supported").
- Anything else → 400 (`Unsupported file type '<suffix>'`).
- Empty content → 400; automatic (non-manual) reviews additionally require
  **≥ 80 words** → 400 naming the actual count.

`POST /api/thinkingstorm/original-feedback` accepts DOCX only (else 400),
rejects payloads over **20 MB**, and returns
`{source_filename, comment_count, comments_text, endnote_text, endnote_source}`
from `feedback_extract.extract_original_feedback`; it never runs a review.

`POST /api/thinkingstorm/feedback/{job_id}` streams the body itself and stops
with **413** once it exceeds `MAX_FEEDBACK_BODY` (128 KB from
`portal.feedback_editor`). Invalid JSON is 400. It then calls
`feedback_editor.save_feedback(OUTPUT_DIR, job_id, payload)` on the threadpool and
maps:

| Condition (from `feedback_editor`) | Status |
| --- | --- |
| Unknown/foreign review or file name (bad `job_id`, path separators, `..`) | 400 |
| No `output/feedback-editor/<job>.json` | 404 |
| Bad or missing `edit_token` | 403 |
| `revision` no longer matches the DOCX | 409 |
| Manuscript, anchors or comment ids changed | 409 |
| Missing/extra comment ids, oversized field, illegal character | 422 |
| Release-gate refusal (`FeedbackSaveError`) | 422 `{detail, issues}` |
| Filesystem `OSError` | 503 |

`GET /api/thinkingstorm/progress/{progress_id}` returns the snapshot from
`review_progress.snapshot(...)`: `status`, `stage`, `message`,
`completed_units`/`total_units`, `completed_passages`/`total_passages`,
`remaining_passages`, `editing_eta_seconds`, `percent` and `elapsed_seconds`; an
unknown or pruned id is **404**.

### Deterministic review engine hand-off

Both review entry points import the engine lazily inside the handler and call it
in this order — the portal supplies text and parameters, the engine owns all
judgement:

| Step | Call | Notes |
| --- | --- | --- |
| Materialise input | `<job_id>_raw.docx` in `OUTPUT_DIR`, either the uploaded bytes verbatim or a DOCX built from sanitised/pasted text | Uploaded bytes are kept so images, tables and fonts survive. |
| Model | `engine.review.docmodel.load_document(path[, academic_style=…])` | Studio passes the style; `/submit` does not. |
| Inline runs | `engine.review.writer.explode_runs(paragraph.element)` per paragraph | Required before rewriting runs. |
| Analysis | `engine.review.analysis.analyze(model)` | Pure, offline rules; no model, no network. |
| Rubric | `engine.review.report.build_review(model, result, text, mode=…, institution=…, student_name=…, reviewer_name=…)` | Returns `overall_score`, `line_edits`, `category_scores`, `executive_summary`, … |
| Commented deliverable | `engine.review.pipeline.review_document(..., feedback_rewriter=feedback_rewriter()[, progress=progress])` | Same entry point in both paths; `/submit` omits `reviewer_initials` and `progress`. `/submit` runs it through `run_in_threadpool`; the Studio path is already inside the threadpool. The result is moved onto the expected filename. |
| Redline | `engine.review.trackchanges.apply_line_edits(src, dst, review_dict["line_edits"], author=…)` | Edits `word/document.xml` in place on a copy of the original. |
| Report | `processor.generate_html_report(review_dict, html_path)` | Rubric scorecard HTML. |

Path-specific behaviour:

- **`/submit`** scrubs first — `scrubber.deidentify(content, student_name=…)`
  returns `(sanitized_text, token_map)`, and the map is stored for
  `/reviewer/approve`, which currently copies the placeholdered DOCX without
  re-identifying it (known defect). It reviews as `reviewer_name="Raunak Banga"`.
  Comments and endnotes are native Word parts of the uploaded file. A
  `PipelineError` from `review_document` becomes HTTP 422 when
  `TS_REVIEW_BACKEND == 'local'` **or** `TS_HUMANIZER == 'local'`; otherwise the
  handler logs "Pipeline declined; legacy fallback" and tries the legacy
  generator. *Note:* that fallback calls `ts_automator`, which this module never
  defines (the Studio path builds a local `automator`), so the branch raises
  `NameError`, is swallowed by its own `except Exception` print, and
  `<job_id>_<stem>_commented.docx` is never written on that path.
- **`/api/thinkingstorm/execute`** has two modes. *Manual* mode (any
  `custom_comments_text` or `custom_endnote_text`) uses
  `ThinkingStormAutomator(reviewer_name=…, initials=…)` with
  `parse_custom_comments_text` / `parse_custom_endnote_text` for exact
  injection, and emits only `reviewing`, `feedback_ready` (0 passages) and
  `document_ready`. *Automatic* mode calls
  `review_document(..., reviewer_initials=…, allow_existing_comments=True, overwrite=True, feedback_rewriter=…, progress=…)`
  and turns a `PipelineError` into **422** — it must never silently fall back.
  Before reviewing a re-uploaded DOCX it strips stale `word/comments.xml` (via
  `tools.strip_comments`) and the previous reviewer's closing letter (via
  `engine.review.source_material.remove_previous_letter`), counting both for the
  response `warning`.
- Studio `job_id` is `ts-<6 hex>`; the response echoes `commented_docx_url`,
  `annotated_docx_url`, `report_url`, `qa_report_url` (`<job_id>_review.json`, the
  engine's own report), `status`, `warning`, `review_quality` (including
  `generation.humanization`), `overall_score`, `executive_summary`, `rubric`,
  `coverage`, `original_feedback`, and the `register_review(...)` fields
  (`editing_available`, `edit_token`, `feedback_revision`, `comments` with
  `feedback_id`, and `endnote_text`; when the anchors cannot be matched it
  instead returns `editing_available: false` plus `editing_unavailable_reason`).
- Studio rows are written with `INSERT OR REPLACE` as `approved` or
  `needs_review`, with `email = "personal.reviewer@apexreview.org"`,
  `docx_filename` = the annotated file and `pii_token_map = '{}'`.

### Feedback save hand-off

`register_review` only grants editing after it proves that each displayed
comment maps 1:1 onto a native `w:comment` with exactly one anchor whose quoted
text matches. It then writes `output/feedback-editor/<job>.json` with the file
names, the hashed capability token (`token_hash`), the anchor list, and the
SHA-256 of `word/document.xml` and of the raw upload.

`save_feedback` re-checks the token (`hmac.compare_digest`), the DOCX revision,
and both stored hashes, rebuilds only the comment bodies and endnote, serialises
them into a temporary copy, runs `engine.review.validate.validate_deliverable`
against the original model and the stored anchors, writes
`<job>_saved_<hash16>.json`, and only then `replace()`s the published DOCX. A
validation failure raises `FeedbackSaveError`, whose `issues` name the offending
field (`comment`/`endnote`/`document`); nothing is published.

### Download endpoints

| Route | Resolution | Failure |
| --- | --- | --- |
| `/download/{filename}` | rejects `'/'`, `'\\'`, `'.'`, `'..'` (404 `detail="File not found"`); then `OUTPUT_DIR / filename` only if it is a file whose resolved parent is `OUTPUT_DIR` | JSON 404 `{"error": "File not found"}` |
| `/download/commented/{job_id}` | scan `OUTPUT_DIR` for `<job_id>_*commented.docx`, download name = filename with the job prefix stripped; then `<job_id>*commented.docx` → `ThinkingStorm_commented.docx`; then delegate to `/download/docx`. Both hits send `Cache-Control: no-store` | falls back, else 404 |
| `/download/docx/{job_id}` | `submissions.docx_filename`; if the file is gone, "healing" scan for `<job_id>_*.docx` | 404 `Document not found for this job ID` / `File missing from output directory` |
| `/download/report/{job_id}` | `submissions.html_filename` | 404 |
| `/samples/institutional-pack.zip` | `samples/Apex_Institutional_Counselor_Sample_Pack.zip` | 404 |

All of them return Starlette `FileResponse`. `/download/{filename}` is
unauthenticated and joins a route parameter onto `OUTPUT_DIR`, but it *does*
confine the result: separators and dot names are rejected and the resolved
parent must equal `OUTPUT_DIR.resolve()`. The other download routes scan
`OUTPUT_DIR` by job-id prefix and do not verify ownership. Stored names are the
de facto contract (known defect).

## Invariants

- **The review judgement stays deterministic and offline.** `engine.review.*` is
  called synchronously (or through `run_in_threadpool` for the long pipeline);
  the portal adds no model call of its own. Model use is selected outside this
  module: `run_portal.py` calls `engine.review_runtime.apply_runtime_defaults()`,
  which seeds `TS_REVIEW_BACKEND`/`TS_HUMANIZER`/`TS_HUMANIZER_CONFIG` from
  `TS_RUNTIME_PROFILE` (default `output/review-runtime.json`) or, failing that,
  sets `TS_REVIEW_BACKEND=local` when `output/local-model/config.json` exists.
  The `local` backend makes the engine call a loopback HTTP model under a token
  budget, while `APEX_ENABLE_LLM=1` gates only `ReviewProcessor`'s OpenAI call,
  which this module never reaches. The portal reads `TS_REVIEW_BACKEND` (and
  `TS_HUMANIZER`) itself only to choose 422 versus legacy fallback.
- **The feedback rewriter is opt-in and guarded.** `feedback_rewriter()` returns
  `None` unless `TS_HUMANIZER=local`, so the default path never calls a model.
  When enabled, the engine masks facts, validates every candidate rewrite
  (`engine/review/humanization.py`), and treats a failure as a `PipelineError`;
  the portal must never turn that into a silent downgrade — `/submit` answers 422
  as soon as `TS_HUMANIZER == 'local'`, and the Studio always answers 422. A
  broken humanizer configuration surfaces as HTTP 503 before any review work.
- **The original document is preserved.** An uploaded DOCX is copied byte-for-byte
  to `<job_id>_raw.docx` and only *copies* are edited; comments/endnotes stay
  native Word parts. Never rebuild the deliverable from extracted text when a
  DOCX was supplied. Known defect: `/submit` dispatches on the lower-cased suffix
  (`server.py:1391`) but decides the verbatim copy with the case-sensitive
  `file.filename.endswith('.docx')` (`server.py:1431`), so `Essay.DOCX` is rebuilt
  from extracted text and loses images, tables and styles; the Studio path
  lower-cases first.
- **A release-gate refusal is surfaced, not masked.** In the Studio path a
  `PipelineError` must become 422, and a `FeedbackSaveError` must become 422 with
  `issues`. In `/submit` it falls back only when neither `TS_REVIEW_BACKEND` nor
  `TS_HUMANIZER` is `local`, logging "Pipeline declined; legacy fallback".
  That fallback is a known defect: it calls the undefined `ts_automator`, raises
  `NameError`, and the bare `except Exception` swallows it; `/submit` still
  redirects to a status page whose commented-download link 404s.
- **Published feedback matches the last validated save.** The Studio's commented
  download is only enabled while the DOCX revision matches the client's draft;
  `save_feedback` publishes by atomic `replace()` after validation, so a reader
  sees either the old or the new package, never a partial one.
- **PII is redacted before review, and re-identification is a known defect.**
  `/submit` computes `sanitized_text` + `pii_token_map` before any engine call and
  stores both; every step appends a `log_compliance_event` row. `approve_job`
  loads the map but never calls `PIIScrubber.reidentify`; it only copies the
  placeholdered DOCX to `_final_certified_<name>.docx` and points
  `docx_filename` at it. The delivered file keeps the placeholder tokens, so
  redaction is currently irreversible in practice.
- **Status machine.** `/submit` inserts rows directly as `in_qa` (the `pending`
  schema default is never written), and `/reviewer/approve` moves them to
  `approved`; Studio rows are inserted as `approved` or `needs_review`. Only
  `client_status` interprets the strings: it maps `in_qa` and `approved` and falls
  back to "Processing" for `needs_review`. `compliance_certificate` never reads
  `status` and is unauthenticated, so `/certificate/{job_id}` issues a "Certified"
  FERPA/IECA certificate for `in_qa` and `needs_review` rows too (known defect).
- **Router ordering is not load-bearing.** `/download/{filename}` is a
  single-segment pattern and cannot capture `/download/commented/{job_id}` or
  `/download/docx/{job_id}`; those routes stay two-segment paths, and
  `/status/{job_id}` stays separate from `/client/status/{job_id}` (the former
  only redirects).
- **Auth gates are per-route and mostly absent.** `get_current_user` is consulted
  by exactly seven handlers: `landing_page`, `thinkingstorm_studio`,
  `reviewer_workbench`, `claim_job`, `calibrate_view`, `approve_job` and
  `request_payout`. The reviewer routes require role `reviewer`/`admin` and
  otherwise 303-redirect to `/login`. Every other route is unauthenticated,
  including `/admin*`, `/submit`, all four Studio APIs (including the feedback
  save), `/client/status/{job_id}`, `/certificate/{job_id}`, `/agency/dashboard`,
  `/download/*`, `/api/health` (job/lead counts and reviewer earnings),
  `/invoices/{invoice_id}` and `/api/voice/baseline`. Do not assume a route is
  protected from its prefix.
- **Claim is idempotent.** `/reviewer/claim` only updates a row whose
  `assigned_reviewer_id` is `NULL`/`''`, so a second reviewer cannot steal a
  claimed job. It does not check that the job exists — the `UPDATE` simply
  affects no rows — and always redirects to the calibration view, which answers
  404 ("Job not found") for an unknown `job_id`.
- **Approval is auditable but not single-shot (known defect).** `approve_job`
  404s on an unknown job, otherwise recomputes the total from the four rubric
  inputs (default 21/20/19/21 = 81), writes a SHA-256 `verification_hash` over
  `job_id:client_name:total_score:now`, credits `300.0` INR with status
  `pending`, and appends to `output/delivery_notifications.log`. There is no
  status or idempotency guard: each POST inserts another `reviewer_earnings` row
  and another delivery notification, so replaying approval pays 300 INR again.
- **DB access is per-request.** Every hit uses `get_db()` (a fresh
  `sqlite3.connect(DB_PATH)` with `row_factory = sqlite3.Row`) inside
  `with get_db() as conn:`; no connection is shared across requests.
- **Import-time side effects are required.** Importing `server` creates
  `output/` and `orchestrator/`, runs `init_compliance_schema()` (which owns
  `reviewer_earnings` and `crm_leads`) and `init_db()` (`submissions`, called at
  `server.py:138`). Any tool or test that imports this module will touch that
  database file.
- **Human-set PII map is JSON.** `pii_token_map` is stored with
  `json.dumps(token_map)` and read with `json.loads`; empty maps are stored as
  `'{}'` by the Studio path.
- **Progress is advisory and bounded.** `review_progress` keeps at most 256
  records, prunes running rows after 7200 s and terminal rows after 900 s,
  rejects a non-`[0-9a-f]{32}` id (400) and a duplicate id (409), and never
  reports 100 % for a failed review. Reviews must succeed even when nothing polls
  or the registry is replaced, because `emit_progress` swallows observer errors.
- **The Studio's HTML comes from the view module.** `thinkingstorm_studio`
  delegates to `portal.thinkingstorm_view`, which reads `static/studio.html` on
  every request and lists the four page scripts; no markup is duplicated in
  `server.py`.

## Side Effects

- **Disk — `output/`**: `<job_id>_raw.docx`, `_annotated.docx`,
  `_commented.docx`, `_report.html`, `_review.json` (QA), `_clean.docx`,
  `_review_clean.docx`, `_saved_<hash16>.json` (each validated feedback save),
  `_final_certified_<name>.docx`, plus `delivery_notifications.log`. `/submit`
  also writes a DOCX built from the pasted text when no file was uploaded.
- **Disk — `output/feedback-editor/`**: `<job>.json` capability state written by
  `register_review` (token hash, anchors, document/raw hashes). It survives across
  restarts, so edits remain possible until the DOCX changes.
- **Disk — `output/humanizer/`**: `review.lock` and the configured
  `config.json`, created/opened by `engine.feedback_humanizer` when a humanizer
  session runs. The lock makes the humanizer slot exclusive across processes.
- **Disk — SQLite `orchestrator/desk_jobs.db`**: `submissions` (inserted by
  `/submit`, `INSERT OR REPLACE` by the Studio, updated by claim/approve),
  `reviewer_earnings` (credited on approval, flipped to `paid` on payout),
  `crm_leads` (checkout and inbound replies), plus the compliance schema created
  by `security.audit_logger`.
- **Compliance trail**: `log_compliance_event(...)` on PII de-identification,
  rubric completion, pipeline decline, review claim, human QA certification and
  commercial booking; `get_job_audit_history` renders that history.
- **Filesystem reads outside the portal**: `samples/` (sample pack),
  `style_corpus/voice_corpus.json` (`/api/voice/baseline`, resolved relative to
  the process working directory), `output/service_status.json` and
  `output/apex_monitor.log` (`/admin/services`).
- **Network**: outbound `smtplib` mail (`/api/mail/send`), the Stripe gateway
  and the institutional invoicing module; the public pages load Tailwind and
  Google Fonts from CDNs (the Studio shell does not). When `TS_HUMANIZER=local`,
  the injected rewriter additionally POSTs to the loopback humanizer endpoint
  (`/v1/models`, `/slots`, then `/completion` or `/v1/chat/completions`) — a call
  owned by `engine/feedback_humanizer.py`, never made directly by this module.
- **Jobs/threads**: `run_in_threadpool` moves the blocking review and the
  feedback save off the event loop; there is no background scheduler, queue
  worker or cache.
- **Process environment**: `TS_HUMANIZER` (`off` default, `local` opt-in)
  selects the injected rewriter and, together with `TS_REVIEW_BACKEND`, decides
  hard-fail (422) versus legacy fallback in `/submit`; `TS_HUMANIZER_CONFIG`
  points at the humanizer config; `TS_RUNTIME_PROFILE` names the JSON profile
  `run_portal.py` seeds those three variables from; `APEX_ENABLE_LLM` gates only
  `ReviewProcessor`'s OpenAI call in `engine/`.
- **Process state**: the module singletons plus the in-memory `review_progress`
  registry (bounded to 256 records, thread-safe). No global mutable request
  state, no locks in this module. Concurrency safety rests on SQLite's default
  file lock (no WAL, no explicit busy timeout), the `feedback_editor.LOCK`
  `RLock` around saves, and distinct `job_id` filenames; a competing writer can
  raise "database is locked".

## Verification

- Run: `python -m unittest discover -s tests` (100 tests, all passing).
- Portal-adjacent suites: `tests/test_studio_js.py` (every linked script parses),
  `tests/test_studio_ui.py` (Studio shell markup), `tests/test_feedback_editor.py`
  (save API, capability token, validation issues) and
  `tests/test_feedback_editor_js.py` (client draft/save/discard lifecycle),
  `tests/test_review_progress.py` (registry bounds, polling endpoint, JS poller),
  `tests/test_clever_widget.py`, `tests/test_feedback_humanizer.py` (rewriter
  transport, guards, `TS_HUMANIZER` gating), `tests/test_original_feedback.py`
  (DOCX comment/endnote extraction), `tests/test_upload_ingest.py` and
  `tests/test_deliverable_integrity.py` (ingest and deliverable preservation).
- Manual smoke: `python run_portal.py`, then `/api/health` for a JSON heartbeat,
  `/thinkingstorm` for the Studio, and `/api/thinkingstorm/progress/<32-hex>` for
  a 404 on an untracked id.
