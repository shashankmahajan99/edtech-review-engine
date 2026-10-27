# Payments (Checkout & Institutional Invoicing)

## Overview

`payments/` turns the desk's commercial catalog into money movement. It has two
independent surfaces:

1. **Checkout gateway** (`stripe_gateway.py`) — can build a hosted Stripe
   Checkout Session for the $150 paid pilot and the three monthly retainer
   tiers, and degrades to a deterministic *simulation* URL when no live key is
   configured. The portal never calls `create_checkout_session`; its
   `/checkout/process` route records the sale directly (see Invariants and
   Risks).
2. **B2B invoicing** (`institutional_invoicing.py`) — issues numbered
   institutional invoices with Net-7 terms and inserts them as `issued` in the
   shared desk database. Nothing in the repository transitions them to `paid` or
   `cancelled`.

Prices do not live only in the checkout catalog. `PACKAGES` is the catalog of
record for checkout, and `/checkout/process` now resolves the submitted
`package_id` through a small alias map (`pilot` → `paid_pilot`) before reading
`PACKAGES` (`portal/server.py:2795-2798`). Invoice amounts are still
caller-supplied, and the portal's invoice API derives them from a substring
match on the human-readable package label (`portal/server.py:4251-4257`), while
the conversion scripts in [`outbound/`](../outbound/EGM.md) hard-code the
figures (including a `$2,000` tier absent from `PACKAGES`). Nothing enforces
consistency.

## Problem & Scope

- The desk needs to collect money for the $150 pilot and three monthly retainer
  tiers, and to issue Net-7 invoices to institutional clients.
- In scope: the `PACKAGES` catalog, checkout-session construction, invoice
  numbering/insertion/read APIs, and the `institutional_invoices` table.
- Out of scope: settlement, reconciliation, receipts, tax, refunds, and the
  portal's checkout UI and routes.
- Consumers: `portal/server.py` (checkout catalog, admin invoice desk) and the
  outbound conversion scripts, which write `transactions` directly rather than
  through this package.

## Goals & Non-Goals

- Goal: one catalog in integer cents covering the four saleable packages.
- Goal: a hosted Stripe session when a key is configured, and a deterministic
  offline simulation URL when it is not.
- Goal: numbered invoices with Net-7 due dates and list/view helpers for the
  admin desk.
- Non-goal: charging a card from the portal. No portal route calls the gateway.
- Non-goal: closing the invoice lifecycle. No `issued` → `paid`/`cancelled`
  transition exists.

## Alternatives Considered

- Hosted Stripe Checkout vs. a custom card form — hosted chosen to avoid card
  data; the portal nonetheless bypasses it and books the sale on form submit.
- Invoice rows in SQLite vs. generated PDFs/email — rows chosen; `pdf_link`
  exists in the schema but is never populated and no PDF is produced.
- Gapless sequential invoice numbers — rejected in favor of date-scoped
  `INV-APX-<YYYYMM>-<6 hex>` ids that tolerate concurrent issuance.
- A separate billing database — rejected in favor of the shared desk database,
  at the cost of import-time DDL and cross-package contention.

## Risks & Mitigations

- **Portal checkout records revenue without a charge (known defect).**
  `/checkout/process` accepts a `payment_method` form field but ignores it,
  inserts a `completed` transaction and advances the CRM to `Pilot
  Booked`/`Retainer Active` for both card and wire, with no Stripe call
  (`portal/server.py:2785-2828`; the stage is chosen purely by
  `amount_dollars >= 1500` at `portal/server.py:2809`). Mitigation: call the
  gateway, or record a pending/unpaid state until a webhook confirms payment.
- **Invoices can never be settled (known defect).** No code updates
  `institutional_invoices.status`; the admin "View / Pay →" link has no payment
  handler. Mitigation: add a status transition route with an audit event.
- **Price drift across surfaces (known defect).** Catalog, portal substring
  matcher, and outbound literals disagree, including an uncatalogued `$2,000`
  tier.
  Mitigation: pass `package_id` through to `PACKAGES` instead of matching
  labels, and import the catalog everywhere else.
- **A Stripe outage looks like a successful simulation.** Gateway exceptions are
  swallowed and a simulation URL is returned, so any future caller can mistake
  an outage for a demo. Mitigation: surface the error and avoid treating a
  simulation as paid.
- **No refund path (known defect).** The SLA's 100% credit refund cannot be
  issued from this package or anywhere else. Mitigation: implement a refund/credit record before
  the remedy is quoted as available.

## Interface

### Module `payments/stripe_gateway.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `PACKAGES` | `Dict[str, Dict]` | Catalog keyed by `paid_pilot`, `starter`, `pro`, `enterprise`; each entry has `name`, `amount_usd` (integer cents), `mode` (`payment` or `subscription`), `description`. |
| `StripeGateway()` | class | Reads `STRIPE_SECRET_KEY` from the environment and sets `stripe.api_key` when both the env var and the `stripe` package are present. |
| `StripeGateway.create_checkout_session(package_id, customer_email, success_url, cancel_url)` | method | Returns `{"url", "session_id", "mode"}` where `mode` is `"live"` (Stripe hosted page) or `"simulation"`; simulation results also carry `package_name` and `amount_usd` in dollars. |

Catalog (amounts in cents): `paid_pilot` 15000 one-off; `starter` 150000/mo;
`pro` 250000/mo; `enterprise` 350000/mo. An unknown `package_id` silently falls
back to `PACKAGES["pro"]`.

### Module `payments/institutional_invoicing.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `PROJECT_ROOT`, `DB_PATH` | `Path` | `<repo>` and `<repo>/orchestrator/desk_jobs.db`. |
| `init_invoicing_db()` | function | Creates `institutional_invoices` if absent. Executed at import time. |
| `create_invoice(client_company, client_email, billing_contact, package_name, amount_usd)` | function | Inserts an `issued` invoice and returns `{invoice_id, client_company, amount_usd, due_date, status}`. |
| `get_all_invoices(limit=25)` | function | Newest-first invoice rows. |
| `get_invoice_by_id(invoice_id)` | function | Single invoice row or `None`. |

Invoice IDs are `INV-APX-<YYYYMM>-<6 upper hex>`; terms are Net 7
(`due_date = created_at + 604800`).

### Table `institutional_invoices`

`invoice_id` (PK), `client_company`, `client_email`, `billing_contact`,
`package_name`, `amount_usd` (REAL, dollars), `status`
(`issued`/`paid`/`cancelled`, default `issued`), `due_date`, `payment_method`
(default `ACH_WIRE_STRIPE`), `pdf_link`, `created_at`, `settled_at` (default 0).

### Consumers

`portal/server.py` imports the invoice helpers `create_invoice`,
`get_all_invoices`, and `get_invoice_by_id` (`portal/server.py:44`), imports
`StripeGateway` and `PACKAGES` (`portal/server.py:51`), and instantiates
`gateway = StripeGateway()` at module load (`portal/server.py:100`). Only the
catalog and the invoice helpers are used to render checkout and the admin
invoice desk; `StripeGateway.create_checkout_session` is never called outside
`stripe_gateway.py`'s own `__main__` block.

## Invariants

- **Cents in the catalog, dollars in the database.** `PACKAGES[*]["amount_usd"]`
  is an integer number of cents; invoice rows and API responses use float
  dollars. Never mix the two in one code path.
- **Simulation must never look like a charge — in the gateway.** Without
  `STRIPE_SECRET_KEY` (or when the Stripe call raises), no network charge occurs
  and the returned URL is the caller's `success_url` with
  `?session_id=sim_...&package=...` appended. A Stripe exception is logged and
  swallowed, then the simulation path runs. This invariant does not protect the
  portal path: `/checkout/process` never calls the gateway and writes a
  `completed` transaction for both card and wire
  (`portal/server.py:2785-2828`), so a "charge" is recorded with no payment call
  at all (known defect).
- **Subscription tiers recur monthly.** `mode == "subscription"` adds
  `price_data.recurring = {"interval": "month"}`; the pilot uses `payment`.
- **Invoice numbering is date-scoped** (`YYYYMM` of issuance) and random-suffixed;
  it is not a gapless sequence.
- **Status vocabulary is declared `issued` → `paid` or `cancelled`, but no
  transition exists (known defect).** `institutional_invoices` defaults to
  `issued`, and no code updates its `status`; the portal's status updates touch
  `submissions` and `reviewer_earnings` only (`portal/server.py:2323-2334`). The
  admin
  console renders a "View / Pay →" link (`portal/server.py:4147`) to the
  read-only invoice page, with no route or handler behind it. Invoices remain
  `issued` permanently and the Net-7 due date has no settlement event.
- **Prices are public policy.** $150 pilot (100% credited toward the first
  retainer), $1,500 / $2,500 / $3,500 monthly tiers, Net-7 institutional terms.
  Update catalog, invoice text, and outreach copy together. There is no
  enforcement: the portal's invoice amount is a substring match on the package
  label (`portal/server.py:4251-4257`) that defaults to `$150`, so renaming a
  tier silently books the pilot price, while checkout resolves `package_id`
  through an alias map into `PACKAGES` and falls back to `paid_pilot`
  (`portal/server.py:2795-2797`). `outbound/` hard-codes figures (including an
  uncatalogued `$2,000`) that no import ties back to `PACKAGES`.
- **Import-time write.** `institutional_invoicing` calls `init_invoicing_db()` at
  module import, so importing it creates or touches the shared database file.

## Side Effects

- **Network:** one HTTPS call to the Stripe API per `create_checkout_session`
  call, only when a secret key and the `stripe` SDK are available. No portal
  route invokes it, so normal portal checkout makes no network call.
- **Disk/database:** creates `institutional_invoices` in
  `orchestrator/desk_jobs.db` at import and inserts invoice rows on
  `create_invoice`.
- **Stdout:** prints a Stripe error line when the live call fails.
- **No filesystem writes** in the simulated path; the simulated URL is returned
  to the caller, not persisted.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite does not import `payments/` directly, but several tests import
  `portal.server` (`tests/test_upload_ingest.py:95`,
  `tests/test_voice_baseline.py:16`), and `portal/server.py:44,51` imports
  `payments.institutional_invoicing` and `payments.stripe_gateway`.
  `institutional_invoicing` runs `init_invoicing_db()` at import
  (`institutional_invoicing.py:79`), so a test run creates the invoicing table in
  the shared database. Smoke check:
  `python -c "import payments.institutional_invoicing, payments.stripe_gateway"`
  (this creates the SQLite tables as a side effect). Checkout flows are exercised
  manually through the portal with and without `STRIPE_SECRET_KEY`; note that
  neither portal path calls Stripe.
