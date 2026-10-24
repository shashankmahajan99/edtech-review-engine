"""Every delivered .docx must carry genuinely native Word comments/endnotes."""
from __future__ import annotations

import sys
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lxml import etree  # noqa: E402

from tools.audit_native import audit  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
FIXTURES = ROOT / "tests" / "fixtures"
OUT = ROOT / "tests" / "_out"


@unittest.skipUnless(FIXTURES.exists(), "fixtures not built")
class TestNativeCommentsAndEndnotes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from portal.server import app

        cls.client = TestClient(app)
        OUT.mkdir(parents=True, exist_ok=True)

    def _review(self, fixture: str):
        source = FIXTURES / fixture
        response = self.client.post(
            "/api/thinkingstorm/execute",
            data={"student_name": "Test Student", "reviewer_name": "Raunak Banga",
                  "reviewer_initials": "RB", "academic_style": "mla", "text": "",
                  "custom_comments_text": "", "custom_endnote_text": ""},
            files={"file": (source.name, source.read_bytes())},
        )
        self.assertEqual(response.status_code, 200, response.text[:300])
        payload = response.json()
        download = self.client.get(f"/download/commented/{payload['job_id']}")
        self.assertEqual(download.status_code, 200)
        path = OUT / f"{payload['job_id']}_{fixture}"
        path.write_bytes(download.content)
        return path

    def test_andrea_is_native(self):
        path = self._review("andrea_raw.docx")
        problems = audit(path)
        self.assertEqual(problems, [], problems)

    def test_kiran_is_native(self):
        path = self._review("kiran_raw.docx")
        self.assertEqual(audit(path), [])

    def test_single_relationship_per_part(self):
        """The fixture already ships an endnotes part; we must reuse its rel."""
        path = self._review("andrea_raw.docx")
        with zipfile.ZipFile(path) as z:
            rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
            types = [r.get("Type") for r in rels
                     if (r.get("Type") or "").rsplit("/", 1)[-1] in {"comments", "endnotes"}]
        self.assertEqual(len(types), len(set(types)))
        self.assertEqual(len(types), 2, types)

    def test_comment_ranges_match_comment_part(self):
        path = self._review("janeen_raw.docx")
        with zipfile.ZipFile(path) as z:
            doc = etree.fromstring(z.read("word/document.xml"))
            comments = etree.fromstring(z.read("word/comments.xml"))
        range_ids = sorted(e.get(f"{W}id") for e in doc.findall(f".//{W}commentRangeStart"))
        ref_ids = sorted(e.get(f"{W}id") for e in doc.findall(f".//{W}commentReference"))
        comment_ids = sorted(c.get(f"{W}id") for c in comments.findall(f"{W}comment"))
        self.assertEqual(range_ids, ref_ids)
        self.assertEqual(range_ids, comment_ids)
        self.assertGreaterEqual(len(comment_ids), 5)


if __name__ == "__main__":
    unittest.main(verbosity=2)
