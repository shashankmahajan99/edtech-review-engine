"""The 120 KB diagnostics are mapped, counted and attached to comments."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review import diagnostics  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestDiagnosticMap(unittest.TestCase):
    def test_all_120_present_and_valid(self):
        entries = diagnostics.entries()
        self.assertEqual(len(entries), 120)
        ids = [e["id"] for e in entries]
        self.assertEqual(len(ids), len(set(ids)))
        for entry in entries:
            self.assertIn(entry["status"], diagnostics.STATUSES)
            if entry["status"] == "mapped":
                self.assertTrue(entry["rules"], entry["id"])
            else:
                self.assertEqual(entry["rules"], [])
                self.assertTrue(entry["reason"], entry["id"])

    def test_mapped_rules_exist(self):
        known = diagnostics._emitted_rules()
        for rule in diagnostics.by_rule():
            self.assertIn(rule, known)

    def test_coverage_counts(self):
        coverage = diagnostics.coverage()
        self.assertEqual(coverage["diagnostics"], 120)
        self.assertEqual(sum(coverage["by_status"].values()), 120)
        self.assertGreaterEqual(coverage["by_status"]["mapped"], 40)
        self.assertGreaterEqual(coverage["by_status"]["human_only"], 50)

    def test_primary_id_is_stable(self):
        self.assertEqual(diagnostics.for_rule("thesis_vague"), "THESIS_CLAIM")
        self.assertEqual(diagnostics.for_rule("subject_verb"), "GRAM_AGREEMENT")
        self.assertIsNone(diagnostics.for_rule("not_a_rule"))

    def test_status_lookup(self):
        self.assertEqual(diagnostics.status("PLAGIARISM_WARNING"), "human_only")
        self.assertEqual(diagnostics.status("GRAM_RUN_ON"), "no_rule")
        self.assertEqual(diagnostics.status("THESIS_CLAIM"), "mapped")


if __name__ == "__main__":
    unittest.main(verbosity=2)
