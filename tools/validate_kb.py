"""Offline validation for the ThinkingStorm-aligned knowledge base.

Usage:
    python tools/validate_kb.py [knowledge/thinkingstorm_kb_v2.json] [legacy.json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


def check(path: Path, legacy: bool = False) -> None:
    data = json.loads(path.read_text(encoding="utf-8"))
    expected = {"persona", "moves", "anti_ai_rules", "endnote_template", "banned_phrases"}
    assert expected.issubset(data), f"missing required keys in {path}"
    if legacy:
        assert set(data) == expected, "legacy file must have exactly five keys"
        assert 12 <= len(data["moves"]) <= 16
    assert len(data["anti_ai_rules"]) >= 8
    moves = data["moves"]
    ids = [m["id"] for m in moves]
    assert len(ids) == len(set(ids))
    for move in moves:
        assert move["labels"] and 4 <= len(move["patterns"]) <= 6
        for pattern in move["patterns"]:
            assert pattern["observation"] and isinstance(pattern["advice"], str)
            assert pattern["length"] in {"short", "medium", "long"}
            if "required_slots" in pattern:
                found = set(re.findall(r"\{([^{}]+)\}",
                                       pattern["observation"] + pattern["advice"]))
                assert found == set(pattern["required_slots"]), move["id"]
            mock = {s: "specific student text"
                    for s in re.findall(r"\{([^{}]+)\}", pattern["observation"] + pattern["advice"])}
            output = (pattern["observation"] + " " + pattern["advice"]).format(**mock)
            assert "{" not in output and "}" not in output
    endnote = data["endnote_template"]
    assert len(endnote["sections"]) in (2, 3)
    assert "Dear " in endnote["opening"]

    if not legacy:
        sources = data["sources"]
        rules = data["diagnostics"]
        keys = set(ids)
        assert len(rules) > 50
        rids = [d["id"] for d in rules]
        assert len(rids) == len(set(rids))
        for diagnostic in rules:
            assert diagnostic["move_id"] in keys, (diagnostic["id"], diagnostic["move_id"])
            assert diagnostic["source_ids"]
            assert all(k in sources for k in diagnostic["source_ids"]), diagnostic["id"]
            assert diagnostic["trigger"] == {
                "op": "verified_issue_flag", "key": diagnostic["id"], "value": True
            }
            assert diagnostic["when_unverified"] == "do_not_emit"
            assert diagnostic["evidence_required"]
        assert all(
            source["url"] is None
            or source["url"].startswith("https://knowledge.thinkingstorm.com/")
            for source in sources.values()
        )

    print("PASS", path.name, "moves=", len(moves),
          "patterns=", sum(len(m["patterns"]) for m in moves),
          "rules=", len(data.get("diagnostics", [])))


if __name__ == "__main__":
    extended = Path(sys.argv[1] if len(sys.argv) > 1
                    else "knowledge/thinkingstorm_kb_v2.json")
    check(extended)
    if len(sys.argv) > 2:
        check(Path(sys.argv[2]), True)
