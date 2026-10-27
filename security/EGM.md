# Security (Auth, PII Scrubbing, Audit Trail)

## Overview

`security/` is the desk's trust boundary. Three modules with distinct jobs:

- `auth.py` — accounts, PBKDF2 password hashing, HMAC-signed session tokens, and
  FastAPI role dependencies.
- `pii_scrubber.py` — best-effort reversible de-identification of student drafts
  before the review pipeline runs. It does not satisfy the FERPA addendum
  published in [`legal/`](../legal/EGM.md): `.docx` uploads are reviewed as the
  original bytes, the token vocabulary is not the addendum's, and the token map
  is persisted. See Invariants and the known deviations below.
- `audit_logger.py` — append-only, SHA-256-stamped compliance trail plus the
  `reviewer_earnings` and `crm_leads` tables that the rest of the desk reads.

The package is imported by `portal/server.py` at startup, and `auth.py` and
`audit_logger.py` both create/seed database state at import time.

## Problem & Scope

- The desk needs local accounts with role gates, a de-identification pass before
  review/model exposure, and a compliance record of job lifecycle events.
- In scope: password/session handling, the regex scrubber and its reversible
  map, and the audit/earnings/CRM tables.
- Out of scope: transport encryption, key management, storage encryption,
  retention/purge, and enforcement of the legal promises in
  [`legal/`](../legal/EGM.md).
- Consumers: `portal/server.py` (startup and every protected route) and the
  outbound modules that read/write `crm_leads`.

## Goals & Non-Goals

- Goal: never persist plaintext passwords; use salted PBKDF2 and expiring,
  signed session tokens.
- Goal: fail closed on role checks for unknown or missing sessions.
- Goal: tokenize the supplied name, emails, phone-shaped strings, and
  `at`/`from`/`attending` schools, and be able to re-identify the deliverable.
- Non-goal: exhaustive anonymization. The scrubber is explicitly best-effort and
  does not cover addresses, Common App IDs, or every school mention.
- Non-goal: a tamper-proof audit log or FERPA certification.

## Alternatives Considered

- An external identity provider vs. a local `users` table — local PBKDF2 chosen
  to keep the desk runnable offline; it also brings seeded demo accounts and a
  hard-coded fallback secret.
- A JWT library vs. the hand-rolled `user_id:role:email:expires_at.hmac` token —
  the hand-rolled token chosen, at the cost of custom parsing/expiry code.
- Keeping the PII map only in memory vs. persisting it for re-identification —
  the database was chosen to regenerate deliverables, which is the root of the
  re-identification exposure.
- A hash chain or external anchor for audit rows — not implemented; a plain
  SHA-256 over the row fields was chosen.

## Risks & Mitigations

- **The re-identification map is persisted beside the raw draft.** Any database
  reader can recover student identities. Mitigation: store the map only for the
  delivery window, encrypt it, and purge `original_text` after review.
- **Tokens embed literal name parts.** `[APPLICANT_<PART>]` is reversible from
  the sanitized text alone. Mitigation: use opaque per-job indices
  (`[APPLICANT_NAME_1]`).
- **`.docx` uploads bypass the scrubber.** The reviewer's and client's Word file
  is built from the original bytes. Mitigation: copy the sanitized text into a
  fresh docx, or redact the original document parts before review.
- **The audit trail is not tamper-evident.** A database writer can rewrite
  `details` and recompute the digest because the seed has no secret and no
  chain. Mitigation: hash-chain rows, anchor the head externally, or sign with a
  key held outside the database.
- **Authentication has deliberate demo bypasses.** Hard-coded master passwords,
  a `shashank` admin shortcut, and a fallback `SECRET_KEY` remain in the code
  (see known deviations). Mitigation: remove them before any real deployment.

## Interface

### Module `security/auth.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `DB_PATH` | `Path` | `security/users.db` (git-ignored via `*.db`). |
| `SECRET_KEY` | `str` | `SESSION_SECRET_KEY` env var, else a hard-coded fallback. |
| `get_user_db()` | function | `sqlite3` connection with `Row` factory (caller closes). |
| `init_user_db()` | function | Creates `users`, back-fills missing columns, seeds four accounts when the table is empty. Runs at import. |
| `register_user(email, raw_pass, role, company, full_name="", payout_upi="", specializations="")` | function | Inserts an `active` user; returns public fields, or `None` on duplicate email. |
| `hash_password(password, salt)` / `verify_password(password, salt, password_hash)` | functions | PBKDF2-HMAC-SHA256, 100,000 iterations, hex digest; verification uses `hmac.compare_digest`. |
| `create_session_token(user_id, role, email)` | function | `"<user_id>:<role>:<email>:<expires_at>.<hmac_sha256 hex>"`, 7-day expiry. |
| `verify_session_token(token)` | function | Parses and signature-checks a token; returns `{user_id, role, email}` or `None` on malformed/expired/bad signature. |
| `authenticate_user(email, password)` | function | Normalizes short aliases (`reviewer`, `admin`, `counselor`, …), then checks master passwords or the stored hash; returns the full user row or `None`. |
| `get_current_user(request)` | function | Reads the `apex_session` cookie and verifies it. |
| `require_role(allowed_roles)` | function | FastAPI dependency factory; raises `401` unless the role is allowed or is `admin`. |

`users` columns: `user_id` (PK, 16 hex), `email` (UNIQUE), `password_hash`,
`salt`, `role` (`counselor`/`reviewer`/`admin`), `company_name`, `full_name`,
`payout_upi`, `specializations`, `status` (`active`/`pending_verification`),
`created_at`.

### Module `security/pii_scrubber.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `PIIScrubber()` | class | Compiles the email, phone, GPA, and school regexes once per instance. |
| `PIIScrubber.deidentify(text, student_name="")` | method | Returns `(sanitized_text, token_map)`. |
| `PIIScrubber.reidentify(sanitized_text, token_map)` | method | Restores originals by exact string replacement over the map. |

Tokens: `[APPLICANT_NAME]` for the full supplied name; per name part
`[APPLICANT_<PART>]` where `<PART>` is the literal uppercased name part (for
"Samantha Vance" the sanitized text contains `[APPLICANT_SAMANTHA]` and
`[APPLICANT_VANCE]`); `[EMAIL_<n>]`, `[PHONE_<n>]`, `[SECONDARY_SCHOOL_<n>]`
with a shared `n` counter starting at 1.

### Module `security/audit_logger.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `DB_PATH` | `Path` | `<repo>/orchestrator/desk_jobs.db` (shared desk database). |
| `get_db()` | function | `sqlite3` connection with `Row` factory. |
| `init_compliance_schema()` | function | Creates `compliance_audit_trail`, `reviewer_earnings`, `crm_leads`. Runs at import. |
| `log_compliance_event(job_id, actor, action_type, details, payload_to_hash="")` | function | Appends one event and returns its `sha256_hash`. |
| `get_job_audit_history(job_id)` | function | All events for a job, oldest first. |

Tables: `compliance_audit_trail` (`event_id` PK 12 chars, `job_id`, `actor`,
`action_type`, `details`, `sha256_hash`, `timestamp`);
`reviewer_earnings` (`amount_inr` default 300.0, `status` default `pending`);
`crm_leads` (unique `email`, `stage` default `Cold Outreached`).

### Related contracts

- [`legal/`](../legal/EGM.md) — the published FERPA/IECA promises these modules
  are meant to implement; the PII gaps are listed under known deviations.
- [`payments/`](../payments/EGM.md) — invoices and checkout sessions.
- [`mail/`](../mail/EGM.md) — spool rows that carry student message bodies.
- [`outbound/`](../outbound/EGM.md) — CRM lead pipeline stored in the same database.

## Invariants

- **Passwords are never stored in plaintext.** Only `salt` (16-byte hex) plus the
  100,000-iteration PBKDF2 hex digest are persisted.
- **Tokens are self-contained and expiring.** Signature covers
  `user_id:role:email:expires_at`; the payload is not encrypted, so it must never
  carry secrets. Expiry is 7 days and enforced on verification.
- **Role checks fail closed for unknown roles.** `require_role` returns `401`
  when no valid session exists; `admin` implicitly passes every role check.
- **De-identification is reversible from the sanitized text, and the map is
  persisted (known defect).** The scrubber is pure, but `token_map` is not the
  sole re-identification key: the per-part token embeds the literal name
  (`security/pii_scrubber.py:39`), so a reader can recover it from the sanitized
  draft alone. The portal also writes `json.dumps(token_map)` into
  `submissions.pii_token_map` (`portal/server.py:1505-1518`), logs the map's
  keys to `compliance_audit_trail.details` (`portal/server.py:1420`), and reads
  the map back on reviewer approval (`portal/server.py:2308-2318`) — though that
  branch only copies the Word file to a `_final_certified_` name and never
  applies the substitutions, so the "re-identification" step is a rename and a
  text/PDF-derived deliverable can ship with tokens still in it. Raw
  `original_text` is stored beside the map (`portal/server.py:1515`). The map is
  therefore neither ephemeral nor the sole key.
- **Mapping is best-effort, not exhaustive.** Only the supplied `student_name`,
  email addresses, phone-shaped strings, and schools introduced by
  `at`/`from`/`attending` are tokenized. The compiled `gpa_pattern` is never
  applied. Do not treat scrubber output as proof of complete anonymization.
- **Name scrubbing is gated.** A name is scrubbed only if longer than two
  characters; individual parts need more than three characters and are skipped
  for the common list `{john, jane, will, may, rose}`.
- **Audit rows are append-only, not tamper-evident or reproducible (known
  defect).** The digest is
  `sha256(job_id:actor:action_type:details:payload:now)` stored in the same
  mutable row as those fields (`security/audit_logger.py:71-78`). There is no
  hash chain, no external anchor, and no secret in the seed. Anyone able to
  write the database can rewrite `details` and recompute a consistent hash, and
  because the seed includes the wall-clock timestamp even an honest auditor
  cannot re-verify a row. There is no update or delete helper, so the trail is
  append-only by convention, not tamper-evident.
- **CRM email is the join key.** `crm_leads.email` is UNIQUE and is used by
  every outbound module and by `close_pilot_deal`/`close_monthly_retainer`.

### Known deviations (documented behaviour, not endorsement)

The current code intentionally trades some hardening for demo convenience. Treat
these as findings for a security review, and do not "fix" them silently in a
documentation-only change:

- `SECRET_KEY` falls back to a hard-coded literal when `SESSION_SECRET_KEY` is
  unset.
- `authenticate_user` accepts a hard-coded master-password set
  (`reviewerpass2026!`, `adminpass2026!`, `password`, `admin`, `reviewer`,
  `123456`, `apex2026`) for any account, bypassing hash verification.
- A login whose email is not in `users` and contains `shashank` returns the first
  `admin` row without any password check (`security/auth.py:139-145`).
- Four seed accounts with fixed passwords (`ReviewerPass2026!`,
  `CounselorPass2026!`, `AdminMaster2026!`) are created by `init_user_db()`
  (`security/auth.py:51-57`).
- The portal persists the PII token map and the raw draft in `submissions`, logs
  the map's keys to the audit trail, and reads the stored map back on approval
  (`portal/server.py:1420`, `1505-1518`, `2308-2318`). This contradicts the
  addendum's "volatile memory" claim.
- The in-portal ThinkingStorm Studio path never runs the scrubber: it stores the
  raw `content` as both `original_text` and `sanitized_text` with
  `pii_token_map = '{}'` (`portal/server.py:1955-1967`), so Studio submissions
  are persisted unredacted.
- Per-part name tokens contain the name itself (`[APPLICANT_SAMANTHA]`), so the
  sanitized text is reversible without the map
  (`security/pii_scrubber.py:39`).
- For `.docx` uploads the file reviewed and redlined is the original bytes
  (`portal/server.py:1430-1438`), so the Word artifact still carries the PII.
- The scrubber emits `[APPLICANT_NAME]`, `[APPLICANT_<PART>]`,
  `[EMAIL_<n>]`, `[PHONE_<n>]`, and `[SECONDARY_SCHOOL_<n>]`; the addendum's
  `[STUDENT_NAME]`, `[HIGH_SCHOOL]`, `[CONTACT_REDACTED]`, and `[APPLICANT_ID]`
  are not produced, and home addresses and Common App IDs are not parsed.

## Side Effects

- **Database writes at import:** `init_user_db()` creates/migrates `users` and
  seeds accounts; `init_compliance_schema()` creates its three tables.
- **Database writes at call time:** user inserts, audit-event inserts, and CRM
  reads in the shared `orchestrator/desk_jobs.db`.
- **Filesystem:** `security/users.db` is created if missing.
- **Environment:** reads `SESSION_SECRET_KEY` once at import; changing it
  invalidates every issued token.
- **Stdout:** the `pii_scrubber` module's `__main__` demo prints an
  original/sanitized/restored audit block; the scrubber itself is silent.
- **No network calls** in this package.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite does not import `security/` directly, but several tests import
  `portal.server` (`tests/test_voice_baseline.py:16`,
  `tests/test_upload_ingest.py:95`, `tests/test_native_ooxml.py:26`), which
  imports `security.auth`, `security.pii_scrubber`, and `security.audit_logger`
  (`portal/server.py:48-50`). Importing `security.auth` creates and seeds
  `security/users.db`, and `audit_logger` creates the compliance tables in
  `orchestrator/desk_jobs.db`, so a test run mutates two databases as a side
  effect. Smoke checks:
  `python -c "import security.auth, security.pii_scrubber, security.audit_logger"`
  (creates/seeds databases) and `python -m security.pii_scrubber` for the demo
  round-trip. Authentication and role gates are exercised manually through the
  portal.
