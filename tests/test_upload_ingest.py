"""Upload ingestion tests: PDF structure recovery and the Studio route."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from engine.review.ingest import pdf_text_to_paragraphs, plain_text_to_paragraphs  # noqa: E402


def make_pdf(lines: list[str]) -> bytes:
    """A minimal one-page PDF with a real text layer (no external library)."""
    parts = ["BT", "/F1 12 Tf", "72 720 Td"]
    for i, line in enumerate(lines):
        safe = line.replace("\\", r"\\").replace("(", r"\(").replace(")", r"\)")
        if i:
            parts.append("0 -18 Td")
        parts.append(f"({safe}) Tj")
    parts.append("ET")
    stream = "\n".join(parts).encode("latin-1")

    objects = [
        b"<</Type /Catalog /Pages 2 0 R>>",
        b"<</Type /Pages /Kids [3 0 R] /Count 1>>",
        b"<</Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources <</Font <</F1 5 0 R>>>> /Contents 4 0 R>>",
        b"<</Length %d>>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<</Type /Font /Subtype /Type1 /BaseFont /Helvetica>>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, start=1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref_at = len(out)
    out += b"xref\n0 %d\n" % (len(objects) + 1)
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += b"%010d 00000 n \n" % off
    out += b"trailer\n<</Size %d /Root 1 0 R>>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, xref_at
    )
    return bytes(out)


SAMPLE_LINES = [
    "Marcus Chen",
    "Professor Alvarez",
    "ENG 210",
    "12 October 2026",
    "The Case for Later Start Times",
    "Schools across the country begin classes before eight in the morning, and students pay for it.",
    "Research on adolescent sleep shows that the teenage circadian rhythm shifts later during puberty.",
    "A later start time would improve attendance and academic performance without changing the curriculum.",
    "According to a 2018 study of 30,000 students, schools that moved their start time to 8:30 saw attendance rise.",
    "The researchers found that students gained nearly an hour of sleep each night, and the gains appeared across",
    "every demographic group in the sample. These gains held steady through the second year of the study.",
    "Critics argue that later start times complicate bus schedules and after-school activities.",
    "However, districts in California and Washington have managed the logistics without cutting programmes.",
    "In conclusion, later start times are the cheapest and best-supported change available, so schools should",
    "move the first bell to 8:30 and give students the sleep their schedules currently take away.",
]


class TestPdfIngest(unittest.TestCase):
    def test_front_matter_and_paragraphs_recovered(self):
        raw = "\n".join(SAMPLE_LINES)
        text = pdf_text_to_paragraphs(raw)
        chunks = [c for c in text.split("\n\n") if c.strip()]
        self.assertGreaterEqual(len(chunks), 6)
        self.assertEqual(chunks[0], "Marcus Chen")
        self.assertIn("12 October 2026", chunks)
        self.assertIn("The Case for Later Start Times", chunks)
        self.assertGreater(len(chunks[-1].split()), 20)

    def test_blank_lines_win(self):
        raw = "First paragraph ends here.\n\nSecond paragraph ends here."
        text = pdf_text_to_paragraphs(raw)
        self.assertEqual(len([c for c in text.split("\n\n") if c.strip()]), 2)

    def test_plain_text_single_newlines(self):
        raw = "\n".join(SAMPLE_LINES)
        text = plain_text_to_paragraphs(raw)
        chunks = [c for c in text.split("\n\n") if c.strip()]
        self.assertGreaterEqual(len(chunks), 6)


class TestStudioPdfRoute(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from portal.server import app

        cls.client = TestClient(app)

    def test_pdf_upload_is_reviewed(self):
        pdf = make_pdf(SAMPLE_LINES)
        response = self.client.post(
            "/api/thinkingstorm/execute",
            data={
                "student_name": "Marcus Chen", "reviewer_name": "Raunak Banga",
                "reviewer_initials": "RB", "academic_style": "mla",
                "text": "", "custom_comments_text": "", "custom_endnote_text": "",
            },
            files={"file": ("essay.pdf", pdf, "application/pdf")},
        )
        self.assertEqual(response.status_code, 200, response.text[:200])
        payload = response.json()
        self.assertGreaterEqual(len(payload["comments"]), 3)
        self.assertEqual(payload.get("warning"), "")
        download = self.client.get(f"/download/commented/{payload['job_id']}")
        self.assertEqual(download.status_code, 200)

    def test_blank_pdf_is_rejected_with_a_reason(self):
        pdf = make_pdf([" "])
        response = self.client.post(
            "/api/thinkingstorm/execute",
            data={
                "student_name": "Scan", "reviewer_name": "RB", "reviewer_initials": "RB",
                "academic_style": "mla", "text": "",
                "custom_comments_text": "", "custom_endnote_text": "",
            },
            files={"file": ("scan.pdf", pdf, "application/pdf")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("selectable text", response.json()["detail"])

    def test_legacy_doc_is_rejected_with_a_reason(self):
        response = self.client.post(
            "/api/thinkingstorm/execute",
            data={
                "student_name": "Doc", "reviewer_name": "RB", "reviewer_initials": "RB",
                "academic_style": "mla", "text": "",
                "custom_comments_text": "", "custom_endnote_text": "",
            },
            files={"file": ("old.doc", b"\xd0\xcf\x11\xe0binary", "application/msword")},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn(".docx", response.json()["detail"])

    def test_short_text_is_rejected_with_a_reason(self):
        response = self.client.post(
            "/api/thinkingstorm/execute",
            data={
                "student_name": "Short", "reviewer_name": "RB", "reviewer_initials": "RB",
                "academic_style": "mla", "text": "Too short to review.",
                "custom_comments_text": "", "custom_endnote_text": "",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("80 words", response.json()["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
