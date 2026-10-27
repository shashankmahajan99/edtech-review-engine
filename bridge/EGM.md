# Bridge (Frontier Consultation)

## Overview

`bridge/` is the human-in-the-loop browser bridge to frontier chat models. It
drives a persistent Microsoft Edge profile either over the Chrome DevTools
Protocol on `127.0.0.1:9222` (`cdp_consultant`, `query_chatgpt.py`) or in a
Playwright context the module launches itself (the dispatcher and the probe
scripts), so an operator can send a strategic brief to ChatGPT ("Astra") or Qwen
and capture the reply as a text/markdown transcript.

It is an operations and strategy tool, not part of the review product: nothing
in `engine/`, `portal/`, `outbound/` or `tests/` imports this package. Quotes it
captures are stored for humans to read, never consumed by the deterministic
review pipeline.

## Problem & Scope

- The review engine is deterministic and offline, so strategic questions about
  it have to go to a frontier chat model from a browser a human has logged into.
- `bridge/` automates only the typing and the DOM scrape around that session:
  it opens a persistent Edge profile and reads the reply out of the page.
- In scope: ChatGPT ("Astra"), Qwen, manual login, and transcript capture under
  `consultation_logs/`.
- Out of scope: credentials, API keys, retries against provider APIs, and any
  consumption of captured text by `engine/`, `portal/`, `outbound/` or `tests/`
  (no test imports this package).

## Goals & Non-Goals

- Goal: one visible, logged-in browser profile (`browser_data/`) that both a
  human and `playwright` can drive on `127.0.0.1:9222`.
- Goal: every successful query leaves a timestamped transcript on disk for a
  human to read.
- Goal: keep the package out of the review runtime — it may break without
  affecting a deliverable.
- Non-goal: reliable unattended completion detection; the dispatcher polls for a
  stop button and otherwise proceeds on a fixed delay (see Invariants).
- Non-goal: portability; several probes hardcode Windows paths and the
  operator's desktop profile.

## Alternatives Considered

- Provider APIs (OpenAI/Qwen keys): rejected implicitly — no key handling exists
  here, and the point is to use the operator's existing web subscriptions.
- Manual copy-paste into the open chat window: still possible via
  `launch_browser`, but rejected as the default because no transcript is saved.
- Headless rendering / server-side scrape: not attempted; every read uses an
  interactive, logged-in profile, and `check_all_profiles` touches the real Edge
  profile only as a probe.
- A CDP-only transport behind `launch_browser`: only `cdp_consultant` and
  `query_chatgpt.py` follow it; the dispatcher and the probes launch their own
  browser instead (see Invariants).

## Risks & Mitigations

- DOM churn on chatgpt.com / chat.qwen.ai: the selectors are unversioned and
  untested, so a frontend rename degrades silently to "wrong text saved" or "no
  text found", reported only through `success`.
- Shared `browser_data/` profile: Chromium admits one browser process per
  user-data-dir, so a self-launching module cannot run alongside
  `launch_browser`; run one path at a time.
- Truncated capture: a dispatcher timeout still returns `success: True` with a
  partial reply, so transcripts must be read, not just counted.
- Session drift: login is manual and persistent; an expired session surfaces as
  "input box not visible" or a missing tab, never as a typed error.

## Interface

- `frontier_dispatcher.FrontierDispatcher(user_data_dir=PROJECT_ROOT/"browser_data")`
  - `.query_chatgpt(prompt, timeout_seconds=120) -> dict` — launches its own
    persistent `msedge` context (it does not attach over CDP), types into the
    ChatGPT composer, and polls for a visible stop button until
    `timeout_seconds` elapses. Returns `{"success": True, "model", "response",
    "saved_to"}` after writing
    `consultation_logs/chatgpt_response_<timestamp>.txt`,
    `{"success": False, "rate_limited": True, "error"}` when a usage-cap string
    is found in the page body, or `{"success": False, "error"}` when the
    composer is not visible or no text is found. `timeout_seconds` bounds only
    the poll loop, not the whole call, and expiry still returns `success: True`
    with whatever is on the page (known defect; see Invariants).
  - `.query_qwen(prompt, timeout_seconds=120) -> dict` — launches its own
    persistent `msedge` context (it does not attach over CDP) against
    `https://chat.qwen.ai` and polls for its own stop selector. Returns
    `{"success": True, "model", "response", "saved_to"}` (file
    `consultation_logs/qwen_response_<timestamp>.txt`) or `{"success": False,
    "error"}`. It has **no** usage-cap branch and never returns `rate_limited`.
  - Module constants: `PROJECT_ROOT`, `USER_DATA_DIR`, `LOGS_DIR`
    (`bridge/consultation_logs`, created at import).
- `cdp_consultant.BrowserConsultant(cdp_url="http://127.0.0.1:9222")`
  - `.check_login_status() -> {"chatgpt": bool, "qwen": bool}` — counts composer
    elements in the already-open tabs; connects over CDP, never launches.
  - `.consult_frontier_thinkers(prompt, target="chatgpt") -> Optional[str]` —
    `target` is `"chatgpt"` or `"qwen"`; returns the latest assistant text and
    writes `consultation_logs/<target>_consultation_<epoch>.md`. It does not
    wait for completion: it sleeps a fixed 8 s, then reads the last match of
    `[data-message-author-role='assistant'], .markdown, .agent-message`, so a
    slow answer is saved truncated (known defect; see Invariants).
  - Module constant `CONSULTATION_LOGS` (created at import).
- `query_chatgpt.main()` — one-shot script with a hardcoded enterprise brief;
  writes `consultation_logs/chatgpt_strategic_guidance.md`.
- `launch_browser.main()` — starts the persistent Edge profile (falls back to
  `chrome`), opens `chatgpt.com` and `chat.qwen.ai`, then blocks until
  `Ctrl+C`; this is the long-lived browser `cdp_consultant` and
  `query_chatgpt.py` attach to — the dispatcher and the probes launch their own.
- `check_all_profiles.check_edge_default()` — headless probe of the *real*
  Edge profile (`%LOCALAPPDATA%\Microsoft\Edge\User Data`); screenshots to
  `output/edge_default_chatgpt.png`.
- `inspect_chatgpt.py`, `inspect_qwen.py`, `test_extract.py` — module-level
  scripts with no functions; they execute on import (there is no `main` guard).
  The two `inspect_*` modules screenshot to `output/chatgpt_view.png` and
  `output/qwen_view.png` plus print page text; `test_extract.py` only prints the
  last three `article` texts and writes nothing except the browser profile.
- `test_frontier_access.test_access()` — manual probe of both tabs and their
  composer visibility.
- `FRONTIER_SUPERVISOR_CONSULTATION.md` — static markdown strategic consultation
  brief sent to ChatGPT ("Astra") and Qwen during human-in-the-loop sessions.
- `consultation_logs/` — captured transcripts (data only, no contract file).
- Sibling contracts: [orchestrator](../orchestrator/EGM.md),
  [scripts](../scripts/EGM.md), [tools](../tools/EGM.md).

## Invariants

- Authentication is manual and persistent: the operator logs in once inside
  `browser_data/`; no module handles credentials, cookies or API keys.
- Two transports exist and are not interchangeable. `cdp_consultant` and
  `query_chatgpt.py` attach with `connect_over_cdp("http://127.0.0.1:9222")`
  and need `launch_browser` (or another browser already listening on 9222);
  started without one they fail at `connect_over_cdp`.
  `frontier_dispatcher.query_chatgpt/query_qwen`, `inspect_chatgpt`,
  `inspect_qwen`, `test_extract` and `test_frontier_access` call
  `launch_persistent_context(...)` themselves and never attach over CDP;
  `test_frontier_access` and the dispatcher also pass
  `--remote-debugging-port=9222`.
- `browser_data/` has one owner at a time. Chromium admits a single browser
  process per user-data-dir, so while `launch_browser` holds the profile the
  self-launching modules fail at launch, before any CDP or page work.
- Every query result is scraped from the DOM, with per-module selectors:
  `query_chatgpt` reads `article, [data-message-author-role='assistant'],
  .markdown`; `query_qwen` reads `.message-content, .markdown,
  .qwen-assistant-message`; `consult_frontier_thinkers` reads the assistant
  union plus `.agent-message`. `success` is reported in the return value and is
  never asserted.
- Rate-limit detection is a substring check on the page body; only
  `query_chatgpt` has that branch, and only it reports `rate_limited`. The check
  runs inside the stop-button poll loop, so a stop button that stays visible for
  the whole `timeout_seconds` exits the loop without ever testing the body.
- Known defect: `query_chatgpt`'s timeout is not a bound on the call. The
  stop-button loop ends at `timeout_seconds`, then a fixed 2 s sleep and the DOM
  read still run, returning `success: True` and saving a possibly truncated
  reply with nothing marking it cut off.
- Known defect: `consult_frontier_thinkers` has no completion check — no stop
  button poll, no timeout — only the fixed 8 s delay above.
- `FrontierDispatcher.query_*` close their self-launched browser in `finally`;
  the two CDP clients never close the browser they attached to; `launch_browser`
  is the intentional exception because its process must stay alive.
- `check_all_profiles.py`, `inspect_chatgpt.py`, `inspect_qwen.py`,
  `test_extract.py` and `test_frontier_access.py` hardcode absolute Windows paths
  (`C:\Users\shashank\edtech-review-engine\browser_data`,
  `%LOCALAPPDATA%\Microsoft\Edge\User Data`, `output\*.png`) and the operator's
  desktop profile; they are machine-specific dev probes, not portable tools.
  Only `launch_browser`, `cdp_consultant` and `frontier_dispatcher` derive paths
  from `__file__`.
- Browser/LLM consultation must stay out of the deterministic review engine:
  nothing here may become a runtime dependency of `engine/review/` (see
  `AGENTS.md`, which forbids model calls and network access there).

## Side Effects

- Network: `https://chatgpt.com` and `https://chat.qwen.ai` through the
  launched browser; no direct HTTP client in this package.
- Disk: creates `browser_data/` (browser profile, also created at import of
  `launch_browser` and on every dispatcher/probe launch) and
  `consultation_logs/` (created at import of `frontier_dispatcher`,
  `cdp_consultant` and `query_chatgpt`); writes timestamped
  `chatgpt_response_*.txt`, `qwen_response_*.txt`, `*_consultation_*.md`;
  screenshots into `output/` (`chatgpt_view.png`, `qwen_view.png`,
  `edge_default_chatgpt.png`).
- Process: spawns visible Edge/Chrome processes — one long-lived instance from
  `launch_browser`, and a fresh one per dispatcher call or probe — all against
  `browser_data/` except `check_all_profiles`, which launches headless against
  the user's real Edge profile and can conflict with a running Edge instance.
- Never edits manuscripts, `engine/review` deliverables, tests or `README.md`.

## Verification

- Run: `python -m unittest discover -s tests`
- The suite does not import `bridge/`; these are manual probes:
  `python bridge/launch_browser.py`, then `python bridge/cdp_consultant.py`
  (login status) or `python bridge/test_frontier_access.py`.
