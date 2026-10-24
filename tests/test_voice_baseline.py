"""Human baseline endpoint: the control condition for detector tests."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class TestVoiceBaseline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from fastapi.testclient import TestClient
        from portal.server import app

        cls.client = TestClient(app)

    def test_baseline_returns_human_text(self):
        response = self.client.get("/api/voice/baseline")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreater(len(payload["text"].split()), 80)
        self.assertGreaterEqual(payload["comments"], 1)
        # real reviewer material, not generated templates
        upper = payload["text"].upper()
        self.assertTrue(any(label in upper for label in
                            ("THESIS", "MLA", "APA", "CONCLUSION", "ORGANIZATION")))
        self.assertTrue(payload["has_endnote"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
