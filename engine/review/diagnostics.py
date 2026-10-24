"""KB diagnostic ids attached to analyser findings.

The knowledge base defines 120 diagnostics; the deterministic analyser covers a
subset.  This module is the single source of truth for that gap: every emitted
comment can carry the diagnostic id it implements, and the coverage report names
what is semantic-only or not implemented rather than pretending otherwise.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MAP_PATH = ROOT / "knowledge" / "diagnostic_map.json"

STATUSES = {"mapped", "human_only", "no_rule"}


@lru_cache(maxsize=1)
def entries() -> list[dict]:
    if not MAP_PATH.exists():
        return []
    data = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    return list(data.get("entries", []))


@lru_cache(maxsize=1)
def by_rule() -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for entry in entries():
        if entry["status"] != "mapped":
            continue
        for rule in entry["rules"]:
            out.setdefault(rule, []).append(entry["id"])
    return out


def for_rule(rule_id: str) -> str | None:
    """Primary KB diagnostic for an analyser rule, if one is mapped."""
    ids = by_rule().get(rule_id)
    return ids[0] if ids else None


def all_for_rule(rule_id: str) -> list[str]:
    return list(by_rule().get(rule_id, []))


def status(diagnostic_id: str) -> str | None:
    for entry in entries():
        if entry["id"] == diagnostic_id:
            return entry["status"]
    return None


def coverage() -> dict:
    counts = {status: 0 for status in STATUSES}
    for entry in entries():
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    unmapped_rules = sorted(
        rule for rule in _emitted_rules() if rule not in by_rule()
    )
    return {
        "diagnostics": len(entries()),
        "by_status": counts,
        "rules_with_diagnostic": len(by_rule()),
        "rules_without_diagnostic": unmapped_rules,
    }


def _emitted_rules() -> set[str]:
    import re

    src = (ROOT / "engine" / "review" / "analysis.py").read_text(encoding="utf-8")
    rules = set(re.findall(r'Finding\(\s*"([a-z_]+)"', src))
    rules |= {"conclusion_and_fragments", "conclusion_and_punctuation", "thesis_and_grammar"}
    return rules
