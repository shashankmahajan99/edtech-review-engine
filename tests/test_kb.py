"""Knowledge-base integration: validation, loading and safe pattern use."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review import kb  # noqa: E402
from engine.review.analysis import analyze  # noqa: E402
from engine.review.docmodel import load_document  # noqa: E402
from engine.review.persona import BANNED_PHRASES  # noqa: E402
from tools.validate_kb import check  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
KB_PATH = ROOT / "knowledge" / "thinkingstorm_kb_v2.json"


class TestKnowledgeBase(unittest.TestCase):
    def test_file_validates(self):
        self.assertTrue(KB_PATH.exists())
        check(KB_PATH)

    def test_counts(self):
        data = kb.load()
        self.assertEqual(len(data["moves"]), 22)
        self.assertEqual(sum(len(m["patterns"]) for m in data["moves"]), 88)
        self.assertEqual(len(data["diagnostics"]), 120)
        self.assertEqual(len(data["sources"]), 80)

    def test_banned_phrases_merged(self):
        lowered = {p.lower() for p in BANNED_PHRASES}
        self.assertIn("be more specific", lowered)
        self.assertIn("it is important to note that", lowered)
        self.assertIn("in today\u2019s ever-evolving world", lowered)

    @unittest.skipUnless(FIXTURES.exists(), "fixtures not built")
    def test_safe_moves_only_and_no_placeholders(self):
        model = load_document(str(FIXTURES / "kiran_raw.docx"))
        result = analyze(model)
        seen = 0
        for finding in result.findings:
            specific, generic = kb.patterns_for_rule(finding.rule_id, model, finding)
            for obs, adv in specific + generic:
                text = obs + " " + adv
                self.assertNotIn("{", text)
                self.assertNotIn("}", text)
                self.assertNotRegex(text, r"\b(?:don't|isn't|it's|you're)\b")
                seen += 1
            move = kb.MOVE_BY_RULE.get(finding.rule_id)
            if move in {"apa", "mla", "grammar"}:
                self.assertEqual(specific + generic, [],
                                 "mechanics moves must keep rule-specific templates")
        self.assertGreater(seen, 0, "no KB pattern was usable at all")


if __name__ == "__main__":
    unittest.main(verbosity=2)
