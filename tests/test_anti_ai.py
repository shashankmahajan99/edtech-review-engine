"""Tests for 26-pattern anti-AI structural scrubber, auditor, and opener archetypes."""
from __future__ import annotations

import unittest

from engine.review.anti_ai_patterns import audit_ai_tells, scrub_ai_tells
from engine.review.persona import classify_opener_archetype, CommentComposer
from engine.review.docmodel import DocumentModel, Paragraph
from engine.review.style_guard import banned_hits


class TestAntiAIPatterns(unittest.TestCase):
    def test_quoted_spans_and_urls_preserved_byte_identical(self):
        text = (
            'https://knowledge.thinkingstorm.com/category/thesis '
            'Cut "in conclusion, we must delve into the multifaceted tapestry of life".'
        )
        scrubbed = scrub_ai_tells(text, seed=42)
        # Quoted text inside double quotes must remain untouched!
        self.assertIn('"in conclusion, we must delve into the multifaceted tapestry of life"', scrubbed)
        self.assertTrue(scrubbed.startswith("https://knowledge.thinkingstorm.com/category/thesis"))

    def test_curly_quotes_preserved(self):
        text = 'Replace “furthermore, the document attempts to navigate the complexities” with plain words.'
        scrubbed = scrub_ai_tells(text, seed=42)
        self.assertIn('“furthermore, the document attempts to navigate the complexities”', scrubbed)

    def test_single_quoted_spans_with_apostrophes_preserved_and_not_flagged(self):
        typo_text = "In ‘In today’s fast-paced world, the author’s claim delves into don’t’, clarify the point."
        scrubbed_typo = scrub_ai_tells(typo_text, seed=42)
        self.assertIn("‘In today’s fast-paced world, the author’s claim delves into don’t’", scrubbed_typo)
        self.assertEqual(audit_ai_tells(scrubbed_typo), [])
        self.assertEqual(banned_hits(scrubbed_typo), [])

        straight_text = "In 'In today's fast-paced world, the author's claim delves into don't', clarify the point."
        scrubbed_straight = scrub_ai_tells(straight_text, seed=42)
        self.assertIn("'In today's fast-paced world, the author's claim delves into don't'", scrubbed_straight)
        self.assertEqual(audit_ai_tells(scrubbed_straight), [])
        self.assertEqual(banned_hits(scrubbed_straight), [])

    def test_zero_contraction_standard_expands_outside_quotes_only(self):
        text = "Don't leave 'don't' or “isn’t” unexplained when it's unclear and you'll revise it."
        scrubbed = scrub_ai_tells(text, seed=42)
        self.assertEqual(
            scrubbed,
            "Do not leave 'don't' or “isn’t” unexplained when it is unclear and you will revise it.",
        )

    def test_banned_discourse_and_runups_scrubbed(self):
        text = "Here's the thing: It is important to note that the study plays a crucial role in the outcome."
        scrubbed = scrub_ai_tells(text, seed=42)
        self.assertNotIn("Here's the thing:", scrubbed)
        self.assertNotIn("It is important to note that", scrubbed)
        self.assertNotIn("crucial role", scrubbed)
        self.assertIn("Note that", scrubbed)

    def test_pattern_not_only_but(self):
        text = "The argument is not only unclear, but also lacks relevant evidence."
        scrubbed = scrub_ai_tells(text, seed=42)
        self.assertNotIn("not only", scrubbed.lower())
        self.assertIn("unclear, and lacks relevant evidence", scrubbed)

    def test_stacked_qualifiers_and_copula(self):
        text = "This paragraph serves as a summary that could potentially confuse readers."
        scrubbed = scrub_ai_tells(text, seed=42)
        self.assertIn("is a summary", scrubbed)
        self.assertNotIn("serves as a", scrubbed)
        self.assertIn("can confuse", scrubbed)
        self.assertNotIn("could potentially", scrubbed)

    def test_audit_ai_tells_detects_patterns(self):
        text = "Furthermore, this paper attempts to delve into the topic."
        tells = audit_ai_tells(text)
        self.assertIn("discourse_markers", tells)
        self.assertIn("delve_into", tells)
        self.assertIn("meta_reference", tells)

    def test_deterministic_reproducibility(self):
        text = "Do not assume that it is necessary to delve into every detail."
        r1 = scrub_ai_tells(text, seed=12345)
        r2 = scrub_ai_tells(text, seed=12345)
        self.assertEqual(r1, r2)

    def test_opener_archetype_classification(self):
        self.assertEqual(classify_opener_archetype('Cut "the result of" from this clause.'), "imperative_quote")
        self.assertEqual(classify_opener_archetype('Why pair "data" with an informal verb?'), "socratic_check")
        self.assertEqual(classify_opener_archetype('You open with a strong claim, yet the evidence is thin.'), "contrastive_claim")
        self.assertEqual(classify_opener_archetype('If you want to persuade readers, cite a study.'), "conditional_fix")
        self.assertEqual(classify_opener_archetype('Too vague here. Add specific metrics.'), "fragment_diagnosis")
        self.assertEqual(classify_opener_archetype('A reader might lose track of the argument here.'), "reader_anchor")


if __name__ == "__main__":
    unittest.main()
