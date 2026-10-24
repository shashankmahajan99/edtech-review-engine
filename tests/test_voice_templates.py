"""Voice guardrails: no meta-commentary, no aphorisms, no word counts."""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review.persona import EXTRAS, TEMPLATES  # noqa: E402

BANNED = [
    "{words}",
    "hundreds of essays",
    "in its own right",
    "is not the same as",
    "only once you tell",
    "at {words}",
]

WORD_COUNT = re.compile(r"\b\d+\s+words\b", re.I)


def _all_template_text() -> str:
    parts = []
    for variants in TEMPLATES.values():
        for observation, advice in variants:
            parts.extend([observation, advice])
    for extras in EXTRAS.values():
        parts.extend(extras)
    return "\n".join(parts)


class TestTemplates(unittest.TestCase):
    def test_no_meta_or_aphorism_phrases(self):
        text = _all_template_text().lower()
        for phrase in BANNED:
            self.assertNotIn(phrase.lower(), text, phrase)

    def test_templates_do_not_reference_word_counts(self):
        self.assertIsNone(WORD_COUNT.search(_all_template_text()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
