# Repository Consolidation and Script Organization

## Problem and User Outcome

The repository root currently contains loose PowerShell daemon scripts, an empty
database file, a redundant git bundle, and top-level single-purpose folders
(`browser_profile`, `prompts`) that duplicate the role of existing components
(`browser_data`, `bridge`).

The goal is to:
1. Relocate operational scripts from root into `scripts/`.
2. Clean up redundant root artifacts (`desk_jobs.db` 0-byte orphan, `edtech_review_engine.bundle`).
3. Consolidate duplicate/overlapping folders:
   - Remove `browser_profile` (empty redundant duplicate of `browser_data`).
   - Merge `prompts/` into `bridge/` and remove `prompts/`.
4. Preserve all runtime behaviors, test passing state, and EGM contract integrity.

## Detailed Scope

### 1. Script Relocation to `scripts/`
Move the following operational and daemon management scripts from repository root to `scripts/`:
- `launch_tunnel.ps1` -> `scripts/launch_tunnel.ps1`
- `start_apex_monitor.ps1` -> `scripts/start_apex_monitor.ps1`
- `start_server_daemon.ps1` -> `scripts/start_server_daemon.ps1`
- `start_ts_watcher.ps1` -> `scripts/start_ts_watcher.ps1`
- `stop_server_daemon.ps1` -> `scripts/stop_server_daemon.ps1`
- `stop_ts_watcher.ps1` -> `scripts/stop_ts_watcher.ps1`
- `run_smtp.py` -> `scripts/run_smtp.py`

Update path resolution inside the moved scripts:
- In `scripts/start_ts_watcher.ps1`: `$root` must resolve to repository root (`Split-Path -Parent $PSScriptRoot`), not `scripts/`.
- In `scripts/stop_ts_watcher.ps1`: `$root` must resolve to repository root.
- In `scripts/start_server_daemon.ps1` and `scripts/stop_server_daemon.ps1`: ensure `$ProjectDir` resolves to repository root.
- Keep `run_portal.py` and `run_poller.py` at root as primary process entry points invoked by `apex_service_monitor.py`.

### 2. Root Cleanup
- Remove 0-byte orphan `desk_jobs.db` from root (active database is `orchestrator/desk_jobs.db`).
- Remove duplicate `edtech_review_engine.bundle` from root (active bundle is `output/edtech_review_engine.bundle`).

### 3. Folder Consolidation
- Remove `browser_profile/` (redundant with `browser_data/`).
- Move `prompts/FRONTIER_SUPERVISOR_CONSULTATION.md` to `bridge/FRONTIER_SUPERVISOR_CONSULTATION.md`.
- Remove `prompts/` directory.

### 4. Contract and Verification Updates
- Update `scripts/EGM.md` to document the moved daemon scripts.
- Update `bridge/EGM.md` to reference `FRONTIER_SUPERVISOR_CONSULTATION.md`.
- Verify all 15 EGM contracts pass validation.
- Verify full test suite (92 tests) passes cleanly.

## Alternatives Considered

1. **Delete all PowerShell scripts**:
   Rejected. These scripts are actively used for 24/7 background daemon
   supervision and the inbox watcher.
2. **Move `run_portal.py` to `scripts/`**:
   Rejected. `run_portal.py` is the documented one-click launcher at root and is
   referenced across documentation and supervisor checks.
3. **Keep `prompts/` as a top-level directory**:
   Rejected. A top-level directory containing a single prompt document for the
   bridge adds clutter; consolidating into `bridge/` groups related artifacts.

## Risks and Mitigations

- **Risk: Moved scripts failing because working directory or relative paths break**:
  *Mitigation*: Adjust `$PSScriptRoot` navigation in PowerShell scripts to
  dynamically resolve `$ProjectDir = (Resolve-Path "$PSScriptRoot\..").Path`.
- **Risk: Broken references in documentation or tests**:
  *Mitigation*: Automated grep across the codebase to ensure no imports or
  subprocess calls break. Full test suite run.

## Verification Gate

1. `python -m unittest discover -s tests`: Must run 92 tests and pass.
2. Verify all moved PowerShell scripts can locate the project directory.
3. Validate all 15 EGM contracts (0 broken links).
