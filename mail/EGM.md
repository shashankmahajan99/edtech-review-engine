# Mail Spool (Local SMTP Desk)

## Overview

`mail/` runs the desk's own RFC 5321/5322 SMTP listener on `127.0.0.1:1025` and
persists every accepted message into the shared `mail_spool` table so the portal
webmail view and the outbound campaign scripts have one audit-able mailbox. It is
the loopback sink for outbound dispatch: campaign code sends to localhost, this
daemon stores the message instead of handing it to a real relay.

The package is a thin wrapper around `aiosmtpd.controller.Controller` plus two
SQLite helpers. It owns no templates and performs no filtering, spam scoring, or
authentication — anything that can reach port 1025 and survives the SQLite
insert is stored; a storage failure is returned to the client as an SMTP error
(see Invariants).

## Problem & Scope

- The outbound scripts need a loopback SMTP sink so a campaign can be exercised
  end to end without a real relay, and the portal needs a webmail view over what
  was sent.
- In scope: the `aiosmtpd` handler, the `mail_spool` table, `init_mail_db`, the
  daemon wrapper, and `get_spooled_mail`.
- Out of scope: actual message delivery, relaying, authentication, spam
  filtering, retry/backoff, and retention/deletion.
- The spool is a local audit of accepted messages, not proof that a message was
  delivered to an external recipient.

## Goals & Non-Goals

- Goal: accept standard SMTP on `127.0.0.1:1025` and persist one row per
  message, including headers and the first plain/HTML body parts.
- Goal: expose newest-first spool rows to the portal webmail page with no
  additional daemon.
- Goal: require no mail-specific database; use the shared desk database.
- Non-goal: RFC-level queue management, bounces, or delivery receipts.
- Non-goal: deduplication by `Message-ID`, purge/retention, or access control on
  stored bodies.

## Alternatives Considered

- Maildir/flat-file mailbox — rejected: the portal already reads the shared
  SQLite database, and a flat file would add a second store to parse.
- A third-party SMTP service or relay — rejected: the desk must run offline and
  campaigns must be demonstrable without external credentials.
- A mail-local SQLite file — rejected in favor of the shared desk database, at
  the cost of lock contention with other writers.
- An async queue/writer between the SMTP handler and SQLite — not implemented;
  `handle_DATA` writes synchronously on the event loop (recorded under Risks).

## Risks & Mitigations

- **SQLite lock contention blocks the SMTP event loop.** Every message runs
  `init_mail_db()` (DDL) and a synchronous INSERT with the driver's default
  5-second busy timeout, no WAL, and no explicit locking, while security,
  payments, outbound, and the portal write the same file and the poller daemon
  reads it. A campaign burst (200 sends) is the worst case. Mitigation: set WAL
  and a busy timeout, move writes to a worker thread/queue, or give mail its own
  database.
- **A storage failure loses the message.** With no try/except the handler
  returns a 5xx to the client and does not spool; there is no disk fallback or
  retry. Mitigation: spool to a file before acknowledging, or return a
  retryable error the sender handles.
- **Unauthenticated listener.** Anything that reaches the port is accepted; the
  loopback default is the only control. Mitigation: keep the bind on loopback
  and put authentication in front of any routable deployment.
- **Bodies and headers are stored indefinitely.** No purge path exists.
  Mitigation: add retention aligned with the FERPA addendum before storing real
  student mail.
- **Direction is a sender-string heuristic.** Mitigation: store the envelope
  direction explicitly when the sender is known.

## Interface

### Module `mail/smtp_server.py`

| Symbol | Kind | Contract |
| --- | --- | --- |
| `PROJECT_ROOT` | `Path` | Repository root (`mail/` parent). |
| `DB_PATH` | `Path` | `<repo>/orchestrator/desk_jobs.db` — the shared desk database, not a mail-local file. |
| `init_mail_db()` | function | Creates `mail_spool` if absent (idempotent, safe to call per request). |
| `ApexMailHandler` | class | `aiosmtpd` handler; implements `async handle_DATA(server, session, envelope)` and returns the SMTP reply string. |
| `ApexSMTPServer(host="127.0.0.1", port=1025)` | class | Owns an `aiosmtpd` `Controller`; `start()` binds and listens, `stop()` shuts down. |
| `get_spooled_mail(limit=25)` | function | Returns newest-first `List[Dict]` rows from `mail_spool`. |

### Table `mail_spool`

`message_id` (PK, `msg_<12 hex>`), `direction`, `sender`, `recipients`,
`subject`, `body_plain`, `body_html`, `headers_json`, `status`
(`queued`/`delivered`/`failed`, default `delivered`), `error_message`,
`timestamp` (epoch float).

### Entry points

- `scripts/run_smtp.py` (repository root) constructs `ApexSMTPServer()` and blocks until
  `KeyboardInterrupt`.
- `portal/server.py` imports `get_spooled_mail` for the webmail page.

## Invariants

- **One row per accepted message.** `handle_DATA` inserts exactly one row with a
  fresh UUID-derived `message_id`; there is no update path and no de-duplication
  by `Message-ID` header.
- **Direction is heuristic.** A message is recorded as `outbound` when the
  envelope sender contains `apex` or `shashank` (case-insensitive), otherwise
  `inbound`. Changing sender addresses changes stored direction.
- **Body extraction takes the first matching part only.** For multipart mail the
  first `text/plain` part becomes `body_plain` and the first `text/html` part
  becomes `body_html`; attachments are discarded (headers are kept as JSON).
- **Accept depends on the insert.** `handle_DATA` writes one row and then
  returns `250 Message accepted for delivery` (`mail/smtp_server.py:72-92`).
  There is no try/except around `init_mail_db()` or the INSERT, so a SQLite
  failure propagates out of the handler; `aiosmtpd` converts an uncaught DATA
  handler exception into a 5xx reply, the 250 line is never reached, and the
  message is not spooled. Storage failures are therefore visible to the client,
  not only in the daemon log.
- **Loopback only by default.** The default bind is `127.0.0.1:1025`; exposing it
  on a routable interface is a deployment decision, not a code default.
- **Shared database.** This package writes into `orchestrator/desk_jobs.db`
  alongside auth, audit, invoicing, and CRM tables; the file is git-ignored
  (`*.db`). Every accepted message runs `init_mail_db()` (a DDL statement) and a
  synchronous `sqlite3` INSERT on the `aiosmtpd` event loop, with the driver's
  default 5-second busy timeout and no WAL or explicit locking, while security,
  payments, outbound, and the portal write the same file and the poller daemon
  reads it. Under contention a campaign burst can block the loop or fail the
  insert; see Risks & Mitigations.

## Side Effects

- Binds a TCP listening socket on `host:port` while the server runs.
- Creates the `mail_spool` table on `init_mail_db()` (also called from
  `ApexSMTPServer.__init__`).
- Inserts message rows, including full plain/HTML bodies and all MIME headers, in
  the shared SQLite database.
- Prints one `[SMTP] Recv ...` line per message to stdout.
- Requires the `aiosmtpd` third-party package at import time.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite has no test for `mail/` behaviour, but it does import the package
  indirectly: several tests import `portal.server`
  (`tests/test_voice_baseline.py:16`, `tests/test_upload_ingest.py:95`), and
  `portal/server.py:43` imports `get_spooled_mail`. Importing the function does
  not run `init_mail_db()`, so a test run only exercises the module import (and
  the `aiosmtpd` dependency); the `mail_spool` table is created on the first
  call to `get_spooled_mail` — the `/admin/mail` webmail route calls it with
  `limit=30` (`portal/server.py:3994-3996`) — or when `ApexSMTPServer` is
  constructed. Smoke check: `python -c "import mail.smtp_server"` (import only,
  no table) and `python -c "from mail.smtp_server import get_spooled_mail;
  get_spooled_mail()"` (creates the table). Starting the daemon
  (`python scripts/run_smtp.py`) is a manual, port-binding operation.
