"""Endnote letters live in the document body, not word/endnotes.xml."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.endnote_extract import body_letter  # noqa: E402


class TestBodyLetter(unittest.TestCase):
    def test_mehak_style_letter_starts_at_praise(self):
        paras = [
            "Works Cited",
            "Smith, John. Title. Publisher, 2020.",
            "You have done a good job to establish the central theme of the essay.",
            "There are a few areas to focus on your next draft. Your thesis is a bit general.",
            "For the next steps, revise the Works Cited entries and check the citations.",
            "This is a good start for your paper. I am looking forward to see how your paper "
            "would develop with these revisions. Best of luck!",
            "Best wishes,",
            "Mehak K.",
        ]
        letter = body_letter(paras)
        self.assertTrue(letter.startswith("You have done a good job"))
        self.assertIn("For the next steps", letter)
        self.assertIn("Best wishes", letter)
        self.assertNotIn("Smith, John", letter)

    def test_mohini_style_letter_keeps_salutation(self):
        paras = [
            "Annotated Bibliography",
            "Dear Erin,",
            "You have done a pretty good job here with the essay. However, there are a few "
            "areas where you need to work.",
            "The thesis needs to be more specific.",
            "I am sure that once you focus on these areas, your writing will look a lot more "
            "refined. I look forward to reading the revised draft. All the best!",
            "Regards,",
            "Mohini.",
        ]
        letter = body_letter(paras)
        self.assertTrue(letter.startswith("Dear Erin,"))
        self.assertIn("Regards", letter)
        self.assertNotIn("Annotated Bibliography", letter)

    def test_no_signature_returns_empty(self):
        self.assertEqual(body_letter(["A paragraph.", "Another paragraph."]), "")

    def test_informal_salutation_is_part_of_the_reviewer_letter(self):
        letter = body_letter(["Student prose.", "Hi Taylor,", "You have done a good job here.",
                              "There are a few areas to focus on.", "Best wishes,", "Mehak K."])
        self.assertTrue(letter.startswith("Hi Taylor,"))
        self.assertNotIn("Student prose.", letter)


if __name__ == "__main__":
    unittest.main(verbosity=2)
