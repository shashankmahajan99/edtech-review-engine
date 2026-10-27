"""The Studio's inline script must parse; a syntax error kills upload/submit."""
from __future__ import annotations

import shutil
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from portal.thinkingstorm_view import get_thinkingstorm_studio_html  # noqa: E402


class TestStudioScript(unittest.TestCase):
    def test_script_parses(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not installed")
        html = get_thinkingstorm_studio_html({"email": "test@example.com"})
        scripts = re.findall(r'<script\b[^>]*src="(/assets/[^"?]+)', html)
        self.assertTrue(scripts, "workspace scripts were not linked")
        for source in scripts:
            path = ROOT / "portal" / "static" / Path(source).name
            result = subprocess.run([node, "--check", str(path)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, f"{path.name}: {result.stderr[-800:]}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
