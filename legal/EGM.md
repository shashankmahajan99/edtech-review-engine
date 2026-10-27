# Legal Contracts (Institutional Compliance Text)

## Overview

`legal/` holds the canonical, human-readable compliance language for
institutional clients: the IECA/NACAC non-ghostwriting attestation, the FERPA
data-protection addendum, and the service-level agreement. It is a
single-module, zero-logic package: the module contains three module-level string
constants and nothing else.

Enforcement of the promises in these texts is split across the desk and only
partially implemented: PII scrubbing in [`security/`](../security/EGM.md)
(best-effort, and undercut by the portal persisting raw drafts and the token
map), payment terms in [`payments/`](../payments/EGM.md) (which has no refund
path), and delivery timing in `portal/server.py` (which measures
`submissions.created_at` itself, not [`mail/`](../mail/EGM.md)). The
`SERVICE_LEVEL_AGREEMENT` constant is not rendered by any portal route. Each gap
is recorded as a known defect under Invariants rather than presented as enforced.

`legal/contracts.py` is imported by the portal
(`portal/server.py:45`) to render two of the three texts into HTML pages:
`IECA_NON_GHOSTWRITING_ATTESTATION` at `/legal/attestation`
(`portal/server.py:4364-4384`) and `FERPA_DATA_PROTECTION_ADDENDUM` at
`/legal/dpa` (`portal/server.py:4387-4407`), both linked from the portal
directory view. `SERVICE_LEVEL_AGREEMENT` is imported but never referenced and
has no route, and no legal text is rendered to PDF anywhere in the repository.
The module performs no I/O, opens no files, and has no import-time side effects.

## Problem & Scope

- The desk quotes ethical, FERPA, and turnaround promises to institutional
  clients; those promises need one canonical source of wording instead of copies
  scattered through portal HTML and outreach templates.
- In scope: the three markdown constants in `legal/contracts.py`, and the two
  portal pages that interpolate them verbatim.
- Out of scope: enforcement. PII scrubbing, refunds, breach detection, and
  retention live (or are missing) in other packages; this package holds only the
  text.
- Consumers: `portal/server.py` renders the attestation and DPA; sales and
  outreach copy paraphrases the same claims in
  [`outbound/`](../outbound/EGM.md).

## Goals & Non-Goals

- Goal: one editable copy of each institutional promise, importable by name and
  safe to read without side effects.
- Goal: publish the attestation and DPA to clients without reformatting, so the
  rendered page and the constant cannot drift.
- Non-goal: making the scrubber match the addendum's token vocabulary — that is
  a [`security/`](../security/EGM.md) change.
- Non-goal: implementing the SLA's refund remedy or the 30-day retention purge.
  Neither exists in the codebase today.
- Non-goal: PDF generation for any legal text.

## Alternatives Considered

- One module per contract (`legal/sla.py`, `legal/dpa.py`, …) — rejected: three
  strings do not justify three import sites, and the portal already imports all
  three from one module.
- Jinja/HTML templates owned by `legal/` — rejected: it would mix presentation
  with the package's deliberate zero-I/O purity; the portal keeps its own page
  shells.
- Storing contract text in the shared SQLite database — rejected: the text is
  versioned with the code, and a database read would add a runtime dependency
  this package avoids.
- Publishing the SLA through a `/legal/sla` route — not implemented; the
  constant is currently imported and unused (known defect).

## Risks & Mitigations

- **The SLA never reaches a client.** `SERVICE_LEVEL_AGREEMENT` is imported and
  unreferenced. Mitigation: add a `/legal/sla` page mirroring the other two, or
  delete the dead import and stop presenting the text as published.
- **The addendum describes tokens the scrubber does not emit.** Mitigation:
  treat the mapping table as illustrative until the scrubber changes, and keep
  the cross-reference in Invariants honest.
- **Remedies and retention are unenforceable.** No refund path and no purge path
  exist. Mitigation: qualify the client-facing text or implement the mechanisms
  before quoting them as guarantees.
- **A text edit silently changes a client-facing promise.** Mitigation: add a
  test that pins the published constants and the routes that render them; none
  exists today.
- **The strings drift from outreach copy.** `outbound/` reproduces the SLA and
  pricing claims by hand. Mitigation: review both surfaces in the same change.

## Interface

### Module `legal/contracts.py`

| Symbol | Kind | Purpose |
| --- | --- | --- |
| `IECA_NON_GHOSTWRITING_ATTESTATION` | `str` | Institutional attestation of ethical editorial integrity: zero-ghostwriting guarantee, admissions-committee alignment, SHA-256 manuscript certificate claims. |
| `FERPA_DATA_PROTECTION_ADDENDUM` | `str` | FERPA (34 CFR Part 99) data-protection addendum: cryptographic PII scrubbing, data sovereignty, anti-training commitment, 30-day retention window. |
| `SERVICE_LEVEL_AGREEMENT` | `str` | 6-hour turnaround SLA with the Early Action / Regular Decision windows and the failure remedy (100% review credit refund + one complimentary priority review). |

There are no functions, classes, dataclasses, or configuration objects in this
package. Consumers import the constants by name; the strings are Markdown.

### Adjacent contracts

- [`mail/`](../mail/EGM.md) — SMTP spool for accepted messages; it is not the
  SLA's source of truth (the countdown uses `submissions.created_at`).
- [`payments/`](../payments/EGM.md) — pilot/retainer pricing and invoicing. No
  refund path exists there or anywhere else, so the SLA remedy is unenforceable
  (known defect).
- [`security/`](../security/EGM.md) — the PII scrubber and audit trail named
  inside the FERPA addendum; the scrubber does not implement the addendum's
  token vocabulary.
- [`outbound/`](../outbound/EGM.md) — commercial outreach that quotes these terms
  to prospects.

## Invariants

- **Zero ghostwriting.** The attestation promises that editors and engines never
  author, ghostwrite, or substitute synthetic prose for student narrative; all
  edits are non-generative tracked OpenXML elements (`<w:ins>`, `<w:del>`,
  `<w:comment>`). Any feature that generates replacement text violates this
  contract.
- **Scrub before exposure (partially enforced; known defect).** The addendum
  states that PII is removed (`[STUDENT_NAME]`, `[HIGH_SCHOOL]`,
  `[CONTACT_REDACTED]`, `[APPLICANT_ID]`) *before* a draft reaches a human
  reviewer or any model path. On the client intake route the sanitized text is
  passed to the report builder (`portal/server.py:1452`) and the scrubber runs
  before the review (`portal/server.py:1419-1420`), but the same request stores
  `original_text` and `json.dumps(token_map)` in `submissions`
  (`portal/server.py:1505-1518`), logs the token keys to
  `compliance_audit_trail` (`portal/server.py:1420`), and the reviewer approval
  route reads the map back (`portal/server.py:2308-2318`) — although it now only
  copies the deliverable under a `_final_certified_` name and never applies the
  substitutions, so the "re-identified" step is effectively a rename. For
  `.docx` uploads the review base is the original bytes, not the sanitized text
  (`portal/server.py:1430-1438`), so the Word file handed to the reviewer still
  carries the student's real name. The in-portal ThinkingStorm Studio path is
  worse: it stores the raw `content` as both `original_text` and
  `sanitized_text` with `pii_token_map = '{}'`
  (`portal/server.py:1955-1967`) and never calls the scrubber. The emitted token
  vocabulary also differs from the addendum's — see
  [`security/EGM.md`](../security/EGM.md) — so the addendum's mapping table is
  illustrative, not literal.
- **No training, no brokers.** Student submissions are never used to train
  commercial foundation models and are never exposed to third-party data
  brokers. This is an absence of such code paths, not an enforced gate.
- **Retention (unimplemented; known defect).** The addendum says files and Word
  markups are kept only for the 30-day SLA retrieval window and purged on
  counselor request. No purge or deletion path exists: `mail/smtp_server.py` has
  no delete statement, `submissions` keeps `original_text` and the PII token
  map, and generated `.docx`/`.html` files remain in `output/`. The 30-day figure
  appears only in `legal/contracts.py`.
- **SLA clock (not measured; known defect).** The agreement text promises 6
  hours from receipt: Early Action/Early Decision October 1 – November 15,
  Regular Decision December 1 – January 15. Commercial surfaces disagree: the
  pricing page sells Desk Starter as "6 to 12-Hour SLA"
  (`portal/server.py:1212`), Desk Enterprise as "4-Hour Priority SLA"
  (`portal/server.py:1253`), and only Desk Pro as "Guaranteed Sub-6-Hour SLA"
  (`portal/server.py:1234`). No code detects a breach: the agency dashboard
  computes a 6-hour deadline and a countdown (`portal/server.py:2924-2938`) but
  prints "Delivered (SLA Met)" for any `approved`/`delivered` job without
  comparing `completed_at` to `created_at + 6h`
  (`portal/server.py:2931-2933`), so the refund remedy has no trigger.
- **Text fidelity.** These constants are published legal language. Do not
  reword, reflow, or "fix" them without an explicit compliance decision; the
  portal interpolates the attestation and addendum verbatim. The SLA constant is
  not routed to any page.

## Side Effects

- None. Importing `legal.contracts` allocates three strings and touches no
  files, network, database, or environment.
- Consumers (`portal/server.py`) interpolate the attestation and DPA constants
  into HTML pages; the only observable effect is outbound HTML text. No PDF
  legal surface exists.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite does not import `legal/` directly, but several tests import
  `portal.server` (`tests/test_voice_baseline.py:16`,
  `tests/test_upload_ingest.py:95`, `tests/test_native_ooxml.py:26`,
  `tests/test_deliverable_integrity.py:81`, `tests/test_review_coverage.py:187`),
  which imports these constants at module load (`portal/server.py:45`). A
  passing run therefore exercises the import, not the contract text: no test
  asserts what these strings say or which routes render them. For a local smoke
  check: `python -c "import legal.contracts"`.
