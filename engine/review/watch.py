"""Background watcher for hands-free ThinkingStorm reviews.

Drop a .docx into the inbox and the watcher produces ``<name>_commented.docx``
plus a JSON QA report in the outbox.  No model calls, no network, no tokens.
"""
from __future__ import annotations

import json
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

from .pipeline import PipelineError, review_document

STOP_FILE = "STOP"
LEDGER = "processed.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_ledger(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
    return {}


def _save_ledger(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _fingerprint(path: Path) -> str:
    stat = path.stat()
    return f"{path.name}:{stat.st_size}:{int(stat.st_mtime)}"


def process_once(inbox: Path, outbox: Path, reviewer: str = "Raunak Banga",
                 initials: str = "RB", style: str = "auto", feedback_rewriter=None) -> list[dict]:
    """Review every new .docx in the inbox once.  Returns per-file results."""
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    done_dir = inbox / "done"
    failed_dir = inbox / "failed"
    ledger_path = outbox / LEDGER
    ledger = _load_ledger(ledger_path)
    results: list[dict] = []

    candidates = sorted(p for p in inbox.glob("*.docx") if not p.name.startswith("~$"))
    for path in candidates:
        key = _fingerprint(path)
        if ledger.get(str(path.resolve())) == key:
            continue
        started = time.time()
        try:
            result = review_document(
                path, output_dir=outbox, reviewer_name=reviewer,
                reviewer_initials=initials, academic_style=style,
                feedback_rewriter=feedback_rewriter,
            )
            done_dir.mkdir(exist_ok=True)
            shutil.move(str(path), str(done_dir / path.name))
            ledger[str(path.resolve())] = key
            results.append({
                "input": path.name,
                "status": "needs_review" if result.quality.get('needs_review') else "ok",
                "review_quality": result.quality,
                "output": Path(result.output_path).name,
                "report": Path(result.report_path).name,
                "comments": len(result.comments),
                "seconds": round(time.time() - started, 2),
            })
        except PipelineError as exc:
            failed_dir.mkdir(exist_ok=True)
            error_path = failed_dir / f"{path.stem}.error.txt"
            error_path.write_text(f"{_now()}\n{exc}\n", encoding="utf-8")
            shutil.move(str(path), str(failed_dir / path.name))
            ledger[str(path.resolve())] = key
            results.append({"input": path.name, "status": "rejected", "error": str(exc)})
        except Exception as exc:  # pragma: no cover - unexpected
            failed_dir.mkdir(exist_ok=True)
            (failed_dir / f"{path.stem}.error.txt").write_text(
                f"{_now()}\nunexpected: {exc}\n", encoding="utf-8"
            )
            results.append({"input": path.name, "status": "error", "error": str(exc)})
        _save_ledger(ledger_path, ledger)

        heartbeat = outbox / "watcher_heartbeat.json"
        heartbeat.write_text(json.dumps({
            "last_run": _now(),
            "processed": len(ledger),
            "last": results[-1] if results else None,
        }, indent=2), encoding="utf-8")
    return results


def run_watcher(inbox: Path, outbox: Path, interval: int = 10,
                reviewer: str = "Raunak Banga", initials: str = "RB",
                style: str = "auto", once: bool = False, feedback_rewriter=None) -> None:
    inbox.mkdir(parents=True, exist_ok=True)
    outbox.mkdir(parents=True, exist_ok=True)
    print(f"[watcher] inbox={inbox} outbox={outbox} interval={interval}s")
    while True:
        if (inbox / STOP_FILE).exists():
            print("[watcher] STOP file found; exiting")
            return
        results = process_once(inbox, outbox, reviewer, initials, style, feedback_rewriter)
        for item in results:
            if item["status"] in {"ok", "needs_review"}:
                print(f"[watcher] {item['status'].upper()} {item['input']} -> {item['output']} "
                      f"({item['comments']} comments, {item['seconds']}s)")
            else:
                print(f"[watcher] {item['input']} REJECTED: {item.get('error')}")
        if once:
            return
        time.sleep(max(1, interval))
