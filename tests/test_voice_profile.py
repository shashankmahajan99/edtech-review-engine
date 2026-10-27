"""Editorial readability checks, without enforcing authorship-detector proxies.

Sentence shapes and variance are descriptive corpus statistics. They must not
cause a complete revision instruction to be shortened or padded.
"""
from __future__ import annotations

import re
import statistics
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review.pipeline import review_document  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
OUT = ROOT / "tests" / "_out"

HEDGES = ["a bit", "a little", "maybe", "perhaps", "seems", "slightly",
          "somewhat", "might", "could", "fairly", "rather"]
CONTRACTIONS = re.compile(r"\b(?:don't|doesn't|isn't|aren't|can't|won't|it's|"
                          r"you're|I'm|I'd|that's|there's|let's|we're|they're)\b", re.I)
BANNED = ["delve", "moreover", "furthermore", "crucial", "comprehensive",
          "nuanced", "tapestry", "underscore", "pivotal", "leverage",
          "holistic", "seamless", "it is important to note"]


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


@unittest.skipUnless(FIXTURES.exists(), "fixtures not built")
class TestEditorialVoice(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(parents=True, exist_ok=True)
        result = review_document(
            str(FIXTURES / "kiran_raw.docx"),
            output_dir=str(OUT),
            overwrite=True,
        )
        cls.bodies = [c["body"] for c in result.comments]

    def test_comment_count_and_length(self):
        self.assertGreaterEqual(len(self.bodies), 8)
        words = [len(b.split()) for b in self.bodies]
        self.assertGreaterEqual(statistics.fmean(words), 14)
        self.assertLessEqual(statistics.fmean(words), 36)

    def test_no_generic_appended_questions(self):
        for body in self.bodies:
            self.assertNotIn("What would that look like here?", body)
            self.assertNotIn("Which sentence would you start with?", body)
            self.assertNotIn("How would you phrase that in one line?", body)

    def test_no_contractions_or_llm_vocabulary(self):
        for body in self.bodies:
            self.assertIsNone(CONTRACTIONS.search(body), body)
            low = body.lower()
            for term in BANNED:
                self.assertNotIn(term, low, body)

    def test_no_word_count_meta(self):
        for body in self.bodies:
            self.assertIsNone(re.search(r"\b\d+\s+words\b", body), body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
