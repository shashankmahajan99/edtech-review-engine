# Scripts (Operational Launchers & macOS Source Sync)

## Overview

`scripts/` holds the operator's host-level operational launchers (PowerShell and
Python) and the Windows-to-macOS source-synchronization utility:
- `start_server_daemon.ps1` & `stop_server_daemon.ps1`: 24/7 background service
  supervisor managing the FastAPI portal (`run_portal.py`), Cloudflare HTTPS
  tunnel (`cloudflared`), SQLite telemetry poller (`run_poller.py`), and host
  supervisor (`orchestrator/apex_service_monitor.py`).
- `start_ts_watcher.ps1` & `stop_ts_watcher.ps1`: Background ThinkingStorm inbox
  watcher wrappers dispatching jobs between `inbox/` and `outbox/`.
- `start_apex_monitor.ps1`: Detached launcher for
  `orchestrator/apex_service_monitor.py`.
- `launch_tunnel.ps1`: Standalone Cloudflare tunnel launcher for
  `http://127.0.0.1:8000`.
- `run_smtp.py`: Apex RFC 5321 loopback SMTP server runner on `127.0.0.1:1025`.
- `sync_to_mac.py`: Source-synchronization utility packaging committed Git refs
  into `edtech_review_engine.bundle` (at root and `output/`) and printing pull
  instructions for the macOS workstation.

None of these scripts are imported by `engine/`, `portal/`, or `tests/`.

## Problem & Scope

- Operational background processes (portal, Cloudflare tunnel, poller, host
  monitor, inbox watcher, and loopback SMTP) and Windows-to-macOS Git bundle
  handoffs need standalone CLI entrypoints outside the application packages.
- `scripts/` provides those host-level wrappers: PowerShell launchers resolving
  the repository root via `$PSScriptRoot\..`, a Python SMTP runner, and the
  one-way Git bundle script.
- In scope: detached process startup/shutdown, PID and log file wiring under
  `output/` and `outbox/`, loopback SMTP startup, and Git bundle creation/push.
- Out of scope: review analysis, healthcheck loops (owned by `orchestrator/`),
  and transferring uncommitted working-tree state (`sync_to_mac.py` never runs
  `git add` or `git commit`).

## Goals & Non-Goals

- Goal: start and stop the background daemon stack and inbox watcher from any
  working directory (`$PSScriptRoot\..` resolution).
- Goal: produce a pullable Git bundle in `output/edtech_review_engine.bundle`
  servable via the portal's `/download/{filename}` route.
- Goal: stay manual and non-destructive on Git remotes unless `--push-to` is
  supplied to `sync_to_mac.py`.
- Non-goal: cross-platform daemon management — the `.ps1` scripts target Windows
  PowerShell / WMI (`Win32_Process`).
- Non-goal: transferring uncommitted edits or git-ignored artifacts (`*.db`,
  `output/`, `browser_data/`).

## Alternatives Considered

- Keeping `.ps1` launchers and `run_smtp.py` at the repository root: consolidated
  into `scripts/` so only `run_portal.py` and `run_poller.py` remain at the root.
- Windows Services / NSSM for daemon supervision: rejected in favor of
  `Start-Process -WindowStyle Hidden` plus PID files (`output/daemon_pids.json`,
  `outbox/watcher.pid`) to avoid administrator installation steps.
- A shared Git remote as the sole macOS sync mechanism: reachable via
  `--push-to`, but `git bundle` remains the default so the Mac can pull over LAN
  without external network access.

## Risks & Mitigations

- `stop_server_daemon.ps1` omits `MonitorPID`: `start_server_daemon.ps1` records
  `ServerPID`, `TunnelPID`, `PollerPID`, and `MonitorPID` in
  `output/daemon_pids.json`, but `stop_server_daemon.ps1` stops only the first
  three. Left running, `orchestrator/apex_service_monitor.py` will respawn
  `run_portal.py` and `run_poller.py` on its next 15-second tick. Mitigation:
  stop the monitor process explicitly (`Get-Process | Where-Object CommandLine -like "*apex_service_monitor.py*" | Stop-Process -Force`).
- Stale bundle served after a failed `git bundle`: `sync_to_mac.py` does not
  delete an earlier bundle on failure, so `output/edtech_review_engine.bundle`
  retains the previous build. Mitigation: check the printed exit status and size.
- Hardcoded LAN address `192.168.29.224:8000` and branch `master` in
  `sync_to_mac.py`: printed pull commands go stale if the host IP or branch
  changes.
- `push_to_remote` in `sync_to_mac.py` is ungated: supplying `--push-to` still
  pushes even if `create_git_bundle()` returned `False`.

## Interface

- `scripts/start_server_daemon.ps1` — kills any running `cloudflared`, deletes
  `output/tunnel.log`, starts `python run_portal.py`,
  `cmd.exe /c "cloudflared tunnel --url http://127.0.0.1:8000 > output\tunnel.log 2>&1"`,
  `python run_poller.py 30`, and `python orchestrator\apex_service_monitor.py`
  hidden, writes `{ServerPID, TunnelPID, PollerPID, MonitorPID, StartedAt}` to
  `output/daemon_pids.json`, sleeps 8 s, and prints the `*.trycloudflare.com`
  URL from `output/tunnel.log`.
- `scripts/stop_server_daemon.ps1` — reads `output/daemon_pids.json`, stops
  `ServerPID`, `TunnelPID`, and `PollerPID` (`MonitorPID` is not stopped; known
  defect), and deletes `output/daemon_pids.json`.
- `scripts/start_apex_monitor.ps1` — stops any existing `apex_service_monitor.py`
  process, starts `python orchestrator\apex_service_monitor.py` hidden, sleeps
  6 s, and prints `output/service_status.json` if present.
- `scripts/launch_tunnel.ps1` — stops any running `cloudflared`, starts
  `cloudflared tunnel --url http://127.0.0.1:8000` hidden with stderr redirected
  to `output/tunnel.log`, sleeps 6 s, and prints `output/tunnel.log`.
- `scripts/start_ts_watcher.ps1` — creates `inbox/` and `outbox/`, removes any
  stale `inbox/STOP` sentinel, checks `Win32_Process` (`Name = 'python.exe'` and
  `CommandLine -like "*engine.review.cli watch*"`) and exits `0` if already
  running, otherwise spawns `python -u -m engine.review.cli watch --inbox <root>/inbox --outbox <root>/outbox --interval 10`
  hidden with stdout to `outbox/watcher.log` and stderr to
  `outbox/watcher.log.err`, writing the PID to `outbox/watcher.pid`.
- `scripts/stop_ts_watcher.ps1` — stops the PID in `outbox/watcher.pid` and
  removes that file; if no PID file existed or the process was already gone,
  queries `Win32_Process` and kills any `python.exe` matching
  `*engine.review.cli watch*`.
- `scripts/run_smtp.py` — inserts `PROJECT_ROOT` (`Path(__file__).resolve().parent.parent`)
  into `sys.path`; under `if __name__ == "__main__":`, instantiates
  `mail.smtp_server.ApexSMTPServer(host="127.0.0.1", port=1025)`, calls
  `.start()`, and sleeps in a 1-second loop until `KeyboardInterrupt` calls
  `.stop()`.
- `scripts/sync_to_mac.py`:
  - `create_git_bundle() -> bool` — runs `git bundle create <repo>/edtech_review_engine.bundle --all`
    and copies the file to `output/edtech_review_engine.bundle`.
  - `display_mac_instructions()` — prints three macOS pull methods (hardcoded
    LAN host `192.168.29.224:8000` and `master` branch).
  - `push_to_remote(remote_url: str)` — removes any existing `mac` remote, adds
    `remote_url`, and runs `git push -u mac master`.
  - `main()` — CLI entrypoint supporting optional `--push-to <git-url>`.
  - Module constants: `ROOT`, `BUNDLE_PATH`, `OUTPUT_BUNDLE_PATH`.
- Sibling contracts: [bridge](../bridge/EGM.md), [mail](../mail/EGM.md),
  [orchestrator](../orchestrator/EGM.md), [tools](../tools/EGM.md).

## Invariants

- All six `.ps1` scripts resolve the repository root via
  `if ($PSScriptRoot) { (Resolve-Path "$PSScriptRoot\..").Path } else { (Get-Location).Path }`,
  and `scripts/run_smtp.py` resolves `PROJECT_ROOT = Path(__file__).resolve().parent.parent`.
- `start_ts_watcher.ps1` enforces single-instance execution via `Win32_Process`
  inspection before spawning; `start_server_daemon.ps1` does not check whether
  `run_portal.py` or `run_poller.py` is already running before spawning new
  instances.
- `stop_server_daemon.ps1` leaves `MonitorPID` alive (known defect), and on
  `start_server_daemon.ps1` `TunnelPID` is the `cmd.exe` wrapper PID rather than
  the child `cloudflared.exe` PID.
- On `sync_to_mac.py` success, the bundle is written both at
  `<repo>/edtech_review_engine.bundle` and `<repo>/output/edtech_review_engine.bundle`;
  only the `output/` copy is served by `/download/edtech_review_engine.bundle`.
- `display_mac_instructions()` runs only when `create_git_bundle()` returns
  `True`, whereas `push_to_remote()` runs unconditionally when `--push-to` is
  passed.

## Side Effects

- Disk: writes `output/daemon_pids.json`, `output/tunnel.log`,
  `outbox/watcher.pid`, `outbox/watcher.log`, `outbox/watcher.log.err`,
  `edtech_review_engine.bundle`, and `output/edtech_review_engine.bundle`;
  deletes `inbox/STOP` (`start_ts_watcher.ps1`), `output/daemon_pids.json`
  (`stop_server_daemon.ps1`), and `outbox/watcher.pid` (`stop_ts_watcher.ps1`).
- Processes: spawns or kills `python.exe` (`run_portal.py`, `run_poller.py`,
  `apex_service_monitor.py`, `engine.review.cli watch`), `cmd.exe`, and
  `cloudflared.exe`; binds `127.0.0.1:1025` in `run_smtp.py`.
- Git state & network: `sync_to_mac.py --push-to` mutates the `mac` git remote
  and pushes `master` over SSH/HTTPS; `start_server_daemon.ps1` and
  `launch_tunnel.ps1` open an outbound Cloudflare edge tunnel.

## Verification

- PowerShell syntax check across all `.ps1` scripts and Python compile check:
  `python -m py_compile scripts/run_smtp.py scripts/sync_to_mac.py`
- Manual bundle smoke test (no remote mutation without `--push-to`):
  `python scripts/sync_to_mac.py`
