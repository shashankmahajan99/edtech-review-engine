"""Word-rendered pagination for page-aware review coverage.

Word stores `w:lastRenderedPageBreak` only when it last saved the document, and
those markers miss pages created by tables, images or a final short page. A
manuscript produced by python-docx has no markers at all, so the engine used to
fall back to a word-count estimate that did not match what Word displays.

This module asks the local Word installation for the page number Word assigns to
each paragraph start, plus the true page count. It opens the input read-only and
never saves or edits it. The pass is optional and local: it is skipped on
non-Windows hosts, when Word is missing, when `TS_WORD_PAGINATION=0`, or when the
COM call fails.
"""
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

_CACHE: dict[tuple[str, float], tuple[list[int], int] | None] = {}


def _powershell_quote(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _script(src: Path) -> str:
    return (
        "$ErrorActionPreference = 'Stop'\n"
        "$word = New-Object -ComObject Word.Application\n"
        "$word.Visible = $false\n"
        "$word.DisplayAlerts = 0\n"
        "try {\n"
        f"  $doc = $word.Documents.Open({_powershell_quote(str(src))}, $false, $true)\n"
        "  $pages = @()\n"
        "  for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {\n"
        "    $p = $doc.Paragraphs.Item($i)\n"
        "    $pages += [int]$doc.Range($p.Range.Start, $p.Range.Start).Information(3)\n"
        "  }\n"
        "  [pscustomobject]@{ pages = [int]$doc.ComputeStatistics(2); paragraphs = $pages } | ConvertTo-Json -Compress\n"
        "  $doc.Close(0)\n"
        "} finally {\n"
        "  $word.Quit()\n"
        "}\n"
    )


def word_paragraph_pages(path: str | Path) -> tuple[list[int], int] | None:
    """Return (page per Word paragraph, page count), or None when unavailable."""
    if os.name != "nt":
        return None
    if os.environ.get("TS_WORD_PAGINATION", "1") in {"0", "false", "no"}:
        return None
    src = Path(path)
    try:
        src = src.resolve()
        key = (str(src), src.stat().st_mtime)
    except OSError:
        return None
    if key in _CACHE:
        return _CACHE[key]
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _script(src)],
            capture_output=True,
            timeout=120,
            text=True,
        )
    except (OSError, subprocess.SubprocessError):
        _CACHE[key] = None
        return None
    if completed.returncode != 0:
        _CACHE[key] = None
        return None
    try:
        payload = json.loads(completed.stdout.strip().splitlines()[-1])
        pages = [int(value) for value in payload["paragraphs"]]
        total = int(payload["pages"])
    except (ValueError, KeyError, IndexError, TypeError):
        _CACHE[key] = None
        return None
    result = (pages, total)
    _CACHE[key] = result
    return result
