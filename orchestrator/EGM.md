# Orchestrator (Host Daemons, Quota Routing, Poller)

## Overview

`orchestrator/` is the host-side operations layer that keeps the review desk
running. It supervises three processes (FastAPI portal on port 8000, the
Cloudflare tunnel, the autonomous poller), holds the multi-model quota registry
that selects which model tier serves a task (the read half — nothing records
exhaustion; see Invariants), and publishes a periodic heartbeat built from the
commercial SQLite database.

It is not imported by the review pipeline. `run_poller.py` at the repository
root is the public entry point for the poller; the supervisor is started from
`scripts/start_server_daemon.ps1` / `scripts/start_apex_monitor.ps1`.

## Problem & Scope

- The review desk has to stay reachable and awake on a Windows host without a
  human session: portal on port 8000, a public quick tunnel, the autonomous
  poller, and no host sleep.
- `orchestrator/` owns host lifecycle (spawn, revive, status JSON) and the
  SQLite data the portal and poller read (quota registry, jobs, CRM leads).
- In scope: process supervision (`apex_service_monitor`), the heartbeat
  (`poller_daemon`), the model registry (`token_manager`), and a DB inspection
  script (`check_db`).
- Out of scope: serving HTTP (`run_portal.py` lives at the repository root),
  binding to any non-loopback interface, and any model call — nothing here
  performs inference.

## Goals & Non-Goals

- Goal: revive the portal within one 15 s loop tick when port 8000 stops
  accepting TCP.
- Goal: keep one poller and one cloudflared alive without double-spawning,
  using the `tasklist` / `wmic` probes; the `server_proc` / `tunnel_proc` /
  `poller_proc` handles are kept but never consulted for liveness.
- Goal: publish `output/service_status.json` and
  `output/daemon_heartbeat.json` often enough for an operator dashboard.
- Non-goal: HTTP-level health checks, tunnel liveness verification, or automatic
  reaction to model rate limits — the write path for exhaustion has no caller
  (see Invariants).
- Non-goal: cross-platform support; `SetThreadExecutionState`, `tasklist`,
  `wmic` and `taskkill` are used directly.

## Alternatives Considered

- A Windows service / Task Scheduler watchdog: not used; the delivered path is a
  Python loop started hidden by `scripts/start_apex_monitor.ps1` or
  `scripts/start_server_daemon.ps1`.
- `pythonw` / NSSM wrappers: not used; the supervisor re-spawns plain `python`
  children (`PYTHON_EXE = sys.executable`).
- Piping cloudflared's output and parsing the URL from the pipe: not done —
  cloudflared is spawned with `DEVNULL`, so URL discovery relies on a sibling
  launcher writing `output/tunnel.log`.
- Polling `/` over HTTP for portal health: not done; liveness is a bare TCP
  connect to 8000.

## Risks & Mitigations

- Tunnel status is cosmetic: `UP` keys off a remembered URL string, including a
  hard-coded seed, so a dead quick tunnel can read `UP`. Mitigation: verify
  `public_url` from a client and treat `UP` as "a URL was remembered".
- Duplicate pollers/tunnels on restart: mitigated only by the `tasklist`/`wmic`
  probes, which fail open — an exception is swallowed and a child is spawned.
- A locked `desk_jobs.db` degrades the heartbeat to zero counts silently; the
  daemon survives but telemetry is wrong.
- The status file is not a health signal for anything but the portal port: the
  poller, database and anti-sleep entries are literals (see Invariants), so a
  dashboard reading `UP` proves only that `update_status_file` ran.
- Anti-sleep holds the host awake indefinitely and the loop never returns; after
  a crash the status file can still describe a healthy host.

## Interface

- `token_manager.TokenManager(db_path=orchestrator/orchestrator.db)`
  - `._init_db()` — creates `model_status` and seeds five models:
    `gpt-6.1-astra`, `gemini-4-argon` (`tier_1_thinker`),
    `gemini-3.8-flash`, `claude-sonnet-5-5`, `gpt-oss-120b` (`tier_2_worker`).
  - `.record_exhaustion(model_slug, cooldown_seconds=3600)` — marks a model
    inactive and stamps `exhausted_at` / bumps `failure_count`. No caller in
    this repository invokes it (known defect; see Invariants).
  - `.check_refresh_status() -> {"refreshed_models": [...], "checked_at": float}`
    — reactivates models whose cooldown has elapsed.
  - `.get_optimal_model(task_type="execution") -> str` — `"heavy_thinking"`
    maps to `tier_1_thinker`, anything else to `tier_2_worker`; falls back to
    any active model, then to the literal `"gemini-3.8-flash"`.
- `poller_daemon.poll_cycle() -> dict` — one heartbeat: token refresh, queue
  counts, aggregate payouts, CRM replies. It also constructs
  `outbound.leads_prospector.LeadManager()` (importing `outbound` and its
  `cold_outreach_templates`) but never uses the object; construction seeds
  `outbound/leads_crm.csv` with five hard-coded placeholder leads when that file
  is absent.
- `poller_daemon.run_poller_daemon(interval_seconds=60)` — loop; the CLI reads
  `sys.argv[1]` with a default of `30`.
- Module constants: `DB_PATH` (`desk_jobs.db`), `OUTPUT_DIR`,
  `HEARTBEAT_FILE` (`output/daemon_heartbeat.json`).
- `apex_service_monitor` — supervision of the host:
  - `enforce_anti_sleep() -> bool`, `log(msg)`, `is_port_listening(port) -> bool`.
  - `ApexServiceSupervisor.start_web_server()`, `.start_cloudflare_tunnel()`,
    `.extract_tunnel_url() -> str`, `.start_poller()`, `.update_status_file()`,
    `.run_supervisor_loop(check_interval_seconds=15)`.
  - Constants: `STATUS_FILE`, `MONITOR_LOG`, `TUNNEL_LOG`, `PORTAL_LOG`,
    `POLLER_LOG`, `PYTHON_EXE`, `CLOUDFLARED_BIN`, `ES_*` Win32 flags.
    `CLOUDFLARED_BIN` is
    `C:\Program Files (x86)\cloudflared\cloudflared.exe`, falling back to the
    bare name `cloudflared` when that path is absent on the host. `PORTAL_LOG`
    and `POLLER_LOG` are declared but never read or written.
- `check_db.py` — module-level script that prints tables, CRM lead stages and
  five sample leads from `desk_jobs.db`.
- Data: `desk_jobs.db` (commercial DB; ten tables including `submissions`,
  `reviewer_earnings`, `crm_leads`, `transactions`, `reviewers`,
  `compliance_audit_trail`, `institutional_invoices` and `mail_spool`;
  `poll_cycle` reads only `submissions`, `reviewer_earnings` and `crm_leads`)
  and `orchestrator.db` (quota registry, `model_status`); both are gitignored by
  the `*.db` rule.
- Sibling contracts: [bridge](../bridge/EGM.md), [scripts](../scripts/EGM.md),
  [tools](../tools/EGM.md).

## Invariants

- Constructing `TokenManager` writes: it creates `model_status` and seeds rows
  with `INSERT OR IGNORE`, so construction is idempotent but never read-only.
- `get_optimal_model` first calls `check_refresh_status`, so a lookup can flip
  `is_active` back to 1; do not treat it as a pure read.
- Within a tier, selection is `ORDER BY failure_count ASC LIMIT 1`; the total
  fallback string `"gemini-3.8-flash"` is hardcoded and need not exist in the
  table.
- Portal liveness is a TCP connect to `127.0.0.1:8000`, not an HTTP check.
  Tunnel status is not a health signal: `update_status_file` reports `UP`
  whenever `self.tunnel_url` contains `trycloudflare.com`, and `__init__` seeds
  that field with a literal `https://…trycloudflare.com` URL; every other value
  reports `CONNECTING`.
- Known defect: the tunnel URL is never invalidated. `extract_tunnel_url`
  returns the seed when `output/tunnel.log` is missing or unmatched, nothing
  clears the URL when cloudflared dies, and because the seed always contains
  `trycloudflare.com` the revive branch in `run_supervisor_loop` never runs;
  `start_cloudflare_tunnel` likewise early-returns while any `cloudflared.exe`
  is alive. A published `public_url` can be dead while `status` is `UP`.
- Known defect: the status file overstates the host. Only the portal entry is
  measured (`is_port_listening(8000)`); `poller_daemon.status` is the literal
  `"UP"` (with a hardcoded `cycle_seconds: 30`), `database.status` is the
  literal `"OPERATIONAL"`, and `anti_sleep_lock.status` is the literal
  `"ACTIVE"` with a hardcoded host string. A dead poller, an unreadable
  `desk_jobs.db` or a failed `SetThreadExecutionState` call cannot show up in
  `output/service_status.json`.
- Known defect: the quota loop has no producer. `record_exhaustion` is defined
  but never called — there is no HTTP 429 handler and no token-budget check — so
  `is_active` stays 1 for all five seeded models, `check_refresh_status` never
  reactivates anything, and `get_optimal_model` always resolves
  `ORDER BY failure_count ASC` over rows whose `failure_count` is 0. Treat
  routing as static until a caller is added.
- The supervisor loop never returns. Any exception is logged and retried after
  5 s; only `KeyboardInterrupt` breaks it. It is single-threaded.
- `poll_cycle` is read-only against `desk_jobs.db` and swallows every database
  error (counts degrade to 0) so a locked DB never kills the daemon. It is not
  side-effect free: it writes the heartbeat and may seed
  `outbound/leads_crm.csv` through `LeadManager()` (see Side Effects).
- The supervisor passes `30` as the poller interval; `run_poller.py`'s own
  default is `30`, and `poller_daemon`'s function default is `60`.
- `check_db.py` hardcodes an absolute `desk_jobs.db` path and runs on import.

## Side Effects

- SQLite: writes `orchestrator/orchestrator.db` (schema, seed rows, status
  flips); reads `orchestrator/desk_jobs.db`.
- Import-time writes: `poller_daemon` and `apex_service_monitor` both call
  `OUTPUT_DIR.mkdir(parents=True, exist_ok=True)` at import, so importing either
  module creates `output/`; `check_db.py` writes nothing but runs on import.
- Disk under `output/`: writes `service_status.json`, `apex_monitor.log`,
  `daemon_heartbeat.json`. Child output is not redirected: `start_web_server`
  inherits stdout/stderr, while the poller and cloudflared are spawned with
  `stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL`; `PORTAL_LOG` and
  `POLLER_LOG` are declared and never used.
- Outbound CRM: `poll_cycle` may create `outbound/leads_crm.csv` with five
  hard-coded placeholder leads via `LeadManager()`; this package calls none of
  `LeadManager`'s other methods.
- URL discovery: `extract_tunnel_url` reads `output/tunnel.log` when it exists.
  The supervisor never writes that file — it is produced by the repository-root
  `scripts/launch_tunnel.ps1` (stderr redirect) and `scripts/start_server_daemon.ps1` (`cmd`
  redirect), so the documented `scripts/start_apex_monitor.ps1` path has no writer.
- Subprocesses: `python run_portal.py`, `python run_poller.py 30`,
  `cloudflared tunnel --url http://127.0.0.1:8000 --no-autoupdate`,
  `tasklist /FI "IMAGENAME eq cloudflared.exe"`,
  `taskkill /F /IM cloudflared.exe`, and a `wmic` query for `run_poller.py`.
- Machine state: `SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED |
  ES_AWAYMODE_REQUIRED)` prevents host sleep while the supervisor runs.
- Network: loopback TCP to `127.0.0.1:8000`; outbound HTTPS only through the
  cloudflared process. Nothing here calls a model API.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite does not cover this package. Manual checks:
  `python orchestrator/check_db.py` (DB contents),
  `python orchestrator/token_manager.py` (tier resolution), and
  `python run_poller.py 30` (one heartbeat cycle, then inspect
  `output/daemon_heartbeat.json`).
