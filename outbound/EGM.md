# Outbound (Lead Pipeline & Campaign Dispatch)

## Overview

`outbound/` is the go-to-market subsystem, but it is not one pipeline: it has
two disjoint lead stores with no synchronization between them.

- **CSV store.** `leads_prospector.py` and `enrich_leads.py` read and rewrite
  `leads_crm.csv`, which currently holds 20 rows: five seeded `DEFAULT_LEADS`,
  three added by hand, and the twelve premier consultancies merged by
  `enrich_crm()`.
- **SQL store.** `execute_campaign.py`, `dispatch_campaign.py`, `deal_closer.py`,
  `scale_conversions.py`, and `ingest_enterprise_leads.py` operate on
  `crm_leads` in `orchestrator/desk_jobs.db`.

Nothing copies rows between the two, so a lead enriched into the CSV is never
dispatched by the SQL sender, and stage changes on a DB lead are invisible to
`EmailDispatcher`. The directory also offers three dispatch paths (staging log,
local SMTP, JSON audit) and conversion scripts that write booked transactions
into the shared desk database. It is operational tooling, not part of the
offline review engine.

Outreach copy and the conversion scripts quote the catalog published in
[`payments/`](../payments/EGM.md) and the legal language in
[`legal/`](../legal/EGM.md), but they reproduce the figures by hand rather than
importing them. Messages either go to a local SMTP sink
([`mail/`](../mail/EGM.md)) or are only written to disk; nothing here talks to
an external SMTP relay unless `SMTP_*` environment variables point at one.

> Operational warning: several modules in this directory act on import or on
> invocation by design (SMTP sends, SQLite writes, and — in
> `scale_conversions.py` / `dispatch_campaign.py` — bulk state changes). Only
> `run_*`/`execute_*` scripts are intended to be run by a human, never by tests
> or CI.

## Package layout

| File | Kind | Entry point | Primary effect |
| --- | --- | --- | --- |
| `cold_outreach_templates.py` | data | — | Three-step outreach copy with `{placeholders}`. |
| `leads_prospector.py` | library | `LeadManager` | Seeds/reads `leads_crm.csv`, renders personalized emails. |
| `email_dispatcher.py` | operator | `EmailDispatcher.dispatch_all()` | Dry-run log by default; live SMTP when asked. |
| `enrich_leads.py` | operator | `enrich_crm()` | Merges 12 premier consultancies into the CSV, deduped by email. |
| `dispatch_campaign.py` | operator | `dispatch_campaign()` | Writes a per-lead letter log and stamps every CRM lead. |
| `execute_campaign.py` | operator | `run_campaign(batch_limit=200)` | Sends real MIME mail, advances CRM stages, writes JSON audit. |
| `deal_closer.py` | library + operator | `close_pilot_deal()`, `close_monthly_retainer()` | Books $150 pilots / monthly retainers as transactions. |
| `scale_conversions.py` | operator | `run_conversion_cycle()` | Idempotent conversion of five named accounts. |
| `scale_client_recruiting.py` | script (no guard) | none | **Executes on import:** rewrites two source files, inserts 77 leads and 11 transactions. |
| `ingest_enterprise_leads.py` | operator | `ingest_leads()` | Inserts 52 named consultancies into `crm_leads`. |
| `leads_crm.csv` | data | — | CSV lead store: header + 20 rows, all `status: Ready`. |
| `dispatch_log.txt`, `campaign_dispatch_v2.log`, `dispatch_audit_20261024.json` | artifacts | — | Recorded dispatch output. |

## Problem & Scope

- The desk needs a repeatable way to prospect agencies, send campaign copy, and
  book the resulting pilots/retainers without a CRM service.
- In scope: CSV and SQLite lead stores, template copy, dispatchers, conversion
  scripts, and the artifacts they write.
- Out of scope: inbound reply handling, unsubscribe suppression, delivery
  tracking, and any model call.
- Two lead stores share no key space or sync job; `crm_leads.email` is unique
  in SQL and the CSV dedupes by lowercased email, but nothing merges the two.

## Goals & Non-Goals

- Goal: run a campaign end to end from local data, with a dry-run path
  (`EmailDispatcher`) and a real-send path (`execute_campaign`).
- Goal: advance CRM stage and write a transaction when a pilot or retainer is
  booked, so revenue and pipeline are visible in the shared database.
- Goal: keep every operator action inspectable after the fact through a log or
  audit JSON.
- Non-goal: guaranteed idempotency. `scale_conversions` retries safely;
  `scale_client_recruiting` and `execute_campaign` do not.
- Non-goal: a single source of truth for lead data or prices.

## Alternatives Considered

- One CSV pipeline for everything — rejected: the portal and SQL dispatchers
  need `crm_leads` rows, and the CSV reader has no concurrent-write story.
- One SQL pipeline for everything — not implemented; the prospect/enrichment
  tooling still writes the CSV.
- A CRM SaaS integration — rejected: the desk is offline-first and the shared
  SQLite file is the system of record.
- A staging queue in front of `execute_campaign` — not implemented; the script
  selects rows and sends directly, so a second run re-mails them.

## Risks & Mitigations

- **Two divergent lead stores.** Totals and stage reports are ambiguous, and
  CSV-enriched leads never reach the SQL dispatcher. Mitigation: pick one store
  or add an explicit import/sync step with a stable external id.
- **`execute_campaign` has no send ledger (known defect).** It selects the first
  200 rows by
  `lead_id` with no stage filter and no already-mailed exclusion, so a re-run
  duplicates external email; ordering across `LEAD-<8 digits>` and
  `lead_<8 hex>` ids is not a stable cohort. Mitigation: record a sent flag per
  lead and select on it.
- **`scale_client_recruiting.py` runs on import and mutates source (known
  defect).** It rewrites `dispatch_campaign.py` and `deal_closer.py`, then
  inserts 11 transactions unconditionally. Mitigation: guard it with `__main__`, make the
  transactions idempotent, and keep it out of imports.
- **Mispricing is silent (known defect).** `deal_closer` books any unrecognised
  retainer label at `$3,500`, and `scale_client_recruiting` books an
  uncatalogued `$2,000` tier. Mitigation: validate against `payments.PACKAGES` and reject unknown
  labels.
- **Marketing copy overstates the product.** Templates promise "under 4 hours"
  and "4 hours 18 minutes average" with no measured data, contradicting the
  6-hour SLA. Mitigation: own the claims in [`legal/`](../legal/EGM.md) and
  derive any quoted average from timed jobs.

## Interface

### `cold_outreach_templates.py`

`IEC_PAID_PILOT_SEQUENCE` — `dict` with keys `step_1_day_1`, `step_2_day_3`,
`step_3_post_pilot_conversion`; each value has `channel`, `subject`, `body`.
Placeholders: `{company_name}`, `{first_name}`, `{upload_link}`, `{sender_name}`,
`{phone_or_whatsapp}`. Copy asserts: sub-6-hour turnaround, "under 4 hours" in
`step_2_day_3`, 100% voice preservation / no ghostwriting, $150 pilot fully
credited, `$1,500/50 reviews` and `$2,500/100 reviews` tiers, and post-pilot net
pricing `$1,350` / `$2,350`. Step 2 also claims "2 senior writing center editors
on standby", and step 3 asserts an "average turnaround time of 4 hours 18
minutes". The 4-hour claims undercut the 6-hour SLA published in
[`legal/`](../legal/EGM.md), and the 4h18m average is not computed anywhere.

### `leads_prospector.py`

- `DEFAULT_LEADS` — five seed leads, all `status: "Ready"`.
- `LeadManager(storage_path=None)` — defaults to `leads_crm.csv` beside the
  module; creates the CSV from `DEFAULT_LEADS` when missing.
- `LeadManager.load_leads()` → `List[Dict]` (CSV rows).
- `LeadManager.generate_personalized_campaign(sender_name="Shashank", upload_link=<cloudflare URL>)`
  → `List[{to_email, company, subject, body}]`.
- `_initialize_storage(leads)` — writes header
  `first_name,last_name,company_name,email,segment,status,website`.

Consumed by `orchestrator/poller_daemon.py` via
`from outbound.leads_prospector import LeadManager`.

### `email_dispatcher.py`

`EmailDispatcher` reads `SMTP_HOST` (default `127.0.0.1`), `SMTP_PORT` (1025),
`SMTP_USER`, `SMTP_PASS`, `SENDER_EMAIL` (default
`editorial-desk@apexreview.co`). `dispatch_all(dry_run=True)` → list of
`{email, status, timestamp}`. Dry-run (the default) appends each rendered
message to `dispatch_log.txt` and never opens a socket; live mode sends
`MIMEMultipart` text through `smtplib.SMTP` with a 10-second timeout and
best-effort STARTTLS/login, sleeping 0.5 s per lead. Failures are captured per
recipient as `Failed: <error>`.

### `enrich_leads.py`

`ADDITIONAL_PREMIER_LEADS` (12 records: first/last name, company, email,
segment, status, website) and `enrich_crm()`, which reloads the CSV, appends
leads whose lowercased email is unseen, and rewrites the file with the canonical
seven-column header.

### `dispatch_campaign.py`

`dispatch_campaign()` reads every row of `crm_leads` in
`orchestrator/desk_jobs.db`, renders a segment-specific letter
(`IEC_Admissions` vs. study-abroad), and writes `campaign_dispatch_v2.log` in
truncating `"w"` mode with one letter per lead. For each lead it sets
`notes` and `last_interaction`, then commits once at the end. `PUBLIC_URL` is a
hard-coded Cloudflare tunnel URL. No mail is sent.

### `execute_campaign.py`

`run_campaign(batch_limit=200)` reads the first `batch_limit` rows of
`crm_leads` ordered by `lead_id` with no stage filter and no exclusion of leads
already mailed (`execute_campaign.py:43-48`), connects to `SMTP_HOST:SMTP_PORT`
(15-second timeout), and sends a plain-text `MIMEMultipart("alternative")`
message per row with `Reply-To = SENDER_EMAIL` (default
`shashank@apexreview.co`). A second run re-mails the same contacts. Ordering by
`lead_id` mixes `LEAD-<8 digits>` and `lead_<8 hex>` ids, so "first 200" is not
a stable cohort. Successful sends move `stage` to
`Outreach Dispatched (Nov 1 Rush)` and set `last_interaction`; the run writes
`dispatch_audit_20261024.json` (`"w"`) only after the loop
(`execute_campaign.py:161-162`), so an uncaught exception earlier in the run
propagates before the audit is written; the `finally` block still quits the SMTP
session.

### `deal_closer.py`

- `init_transactions_table()` — creates `transactions` (`transaction_id` PK,
  `client_email`, `company_name`, `package`, `amount_usd`, `status` default
  `completed`, `timestamp`).
- `close_pilot_deal(lead_email, simulated_reply_text="")` — requires an existing
  `crm_leads` row; sets stage `Pilot Booked`, records a `TX-<8 hex>` transaction
  for `$150.00`, prints a closing brief, returns
  `{status, tx_id, company, amount, stage}` or `{"status": "error", ...}`.
  The `simulated_reply_text` argument is accepted but unused.
- `close_monthly_retainer(lead_email, package_name="Desk Pro")` — `Desk Pro`
  2500, `Desk Starter` 1500, anything else 3500; stage `Retainer Active`;
  transaction prefix `RET-`. **Known defect:** the tier lookup is an exact string
  match (`deal_closer.py:99`); a caller passing `desk pro`, `Desk Pro Retainer`,
  or a new tier silently books `$3,500` and the returned dict still reports
  success. There is no validation against `payments.PACKAGES` and no error path.
- `run_commercial_acceleration_cycle()` — demo driver that closes three pilots
  and one retainer, then prints pipeline telemetry from `transactions` and
  `crm_leads`.

### `scale_conversions.py`

`ACCOUNTS_TO_CONVERT` (five companies with package, amount, and canned reply)
and `run_conversion_cycle()`: creates `transactions` if absent, skips accounts
that already have a transaction row (idempotent by `client_email`), assigns
`Retainer Active` when `amount_usd >= 1500` else `Pilot Booked`, appends the
reply to `crm_leads.notes`, and prints revenue/pipeline telemetry.

### `scale_client_recruiting.py`

Top-level script with **no functions and no `__main__` guard**. Importing or
running it: (1) regex-rewrites `PUBLIC_URL` inside `dispatch_campaign.py` and
`deal_closer.py` to the hard-coded `LIVE_EDGE_URL`; (2) `INSERT OR IGNORE`s 77
consultancies into `crm_leads` with fresh `lead_<8 hex>` ids; (3) inserts six
$150 pilot transactions and updates those leads; (4) inserts five retainer
transactions (three at `$2,500`, two at `$2,000`) and upgrades those leads;
(5) prints totals. It assumes `transactions` already exists and does not create
it. The literal list contains 77 tuples; the module docstring's claim of a
119-to-200 expansion is wrong.

### `ingest_enterprise_leads.py`

`NEW_LEADS` — 52 tuples `(first_name, last_name, company, email, location,
website)` (42 US practices + 10 international) and `ingest_leads()`: creates
`crm_leads` if absent, inserts each lead as `Cold Outreached` with
`segment = "IEC_Admissions"` and a location note, swallowing `IntegrityError`
for existing emails, then prints the added/total count.

## Invariants

- **Never send mail from tests or CI.** `email_dispatcher.dispatch_all()` defaults
  to `dry_run=True`; `execute_campaign.run_campaign()` sends immediately with no
  dry-run switch. Neither is imported by `tests/`.
- **`crm_leads.email` is the identity key.** Every stage update, transaction
  booking, and dedupe in this directory joins on the email address; the schema
  itself is created by `security/audit_logger.py` — see
  [`security/`](../security/EGM.md).
- **Stage vocabulary:** `Cold Outreached` → `Inbound Replied` → `Pilot Booked` →
  `Retainer Active`, plus `Outreach Dispatched (Nov 1 Rush)` written by
  `execute_campaign.py`.
- **Money is USD floats** in `transactions.amount_usd`; the catalog of record is
  `payments/stripe_gateway.py` (which stores cents). `deal_closer` and
  `scale_client_recruiting` hard-code `$150`, `$1,500`, `$2,000`, `$2,500`, and
  `$3,500` figures instead of importing the catalog — a price change must be
  applied here manually. `$2,000` is not a catalog tier at all: `PACKAGES` has
  only 15000/150000/250000/350000 cents, yet
  `scale_client_recruiting.py:173-179` books two retainers at `2000.0` under the
  label "Apex Dedicated Retainer (Tier 1 Standard)". This is uncatalogued
  revenue, recorded as a known defect rather than a routine copy of a published
  price.
- **Claims in copy must match the product.** The templates and letters assert
  6-hour SLA, native Word track changes, 4-pillar rubric, PII scrubbing, and zero
  ghostwriting. Those claims are contracts owned by
  [`legal/`](../legal/EGM.md); do not strengthen them in marketing text alone.
  The templates already violate this: `step_2_day_3` promises "under 4 hours"
  and `step_3_post_pilot_conversion` quotes an "average turnaround time of 4
  hours 18 minutes" that no code computes, both undercutting the 6-hour SLA.
- **Delivery artifacts are overwritten, not appended** (`dispatch_campaign.py`
  and `execute_campaign.py` both open in `"w"` mode); `email_dispatcher.py`
  appends to `dispatch_log.txt`. Keep that distinction when reading logs.
- **Idempotency is uneven.** `scale_conversions.py` skips already-booked emails;
  `scale_client_recruiting.py` inserts its 11 transactions unconditionally and
  therefore double-books revenue if run twice. `execute_campaign.py` has no
  sent-lead filter either: a second run re-mails every selected row.
- **`scale_client_recruiting.py` mutates source code.** It rewrites
  `dispatch_campaign.py` and `deal_closer.py` at import. Do not import it from
  application code, and expect a dirty working tree after running it.
- **Lead IDs built from `hash(email)` are not stable** across processes
  (`ingest_enterprise_leads.py`), so they cannot be used as durable external
  references; email uniqueness is what prevents duplicates.
- **CSV schema is fixed** to the seven columns in `LeadManager._initialize_storage`;
  `enrich_crm()` rewrites the file and will drop any extra columns.
- **Relative imports** (`from .leads_prospector import …`) require importing the
  directory as a namespace package from the repository root; there is no
  `outbound/__init__.py`.

## Side Effects

- **Email:** local-SMTP or relayed SMTP sends (`email_dispatcher.py`,
  `execute_campaign.py`) to real external addresses listed in the CRM.
- **Filesystem writes:** `leads_crm.csv` (create/rewrite), `dispatch_log.txt`
  (append), `campaign_dispatch_v2.log` (truncate), `dispatch_audit_20261024.json`
  (truncate), and in-place edits to `dispatch_campaign.py` / `deal_closer.py`.
- **Database writes:** `orchestrator/desk_jobs.db` — `crm_leads` inserts and
  stage/notes/timestamp updates, `transactions` inserts.
- **Stdout:** progress banners, per-lead dispatch/error lines, closing briefs,
  and revenue telemetry; stderr is unused.
- **Network:** SMTP sockets only (plus the hard-coded Cloudflare tunnel URL
  embedded in message bodies — no fetch of that URL is performed here).
- **Timing:** `execute_campaign` sleeps 0.05 s per lead; `email_dispatcher` sleeps
  0.5 s per lead.

## Verification

- Run: `python -m unittest discover -s tests`
- `tests/` does not import `outbound/`; the suite covers `engine/` and the
  portal's rendered scripts, and it never sends mail or touches `crm_leads`. Do
  not add these scripts to automated tests while they send mail or write the
  shared database. Safe smoke checks:
  `python -c "import outbound.leads_prospector"` and
  `python -c "from outbound.leads_prospector import LeadManager; print(len(LeadManager().load_leads()))"`
  (read-only against the CSV). Running any `run_*`/`execute_*` entry point is a
  manual, human-supervised operation.
