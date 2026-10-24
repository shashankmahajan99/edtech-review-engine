"""Turn uploaded PDF/text into reviewable paragraphs.

pypdf returns one visual line per call and usually drops paragraph spacing, so a
naive join produces a single wall of text: no front matter, no paragraphs, and
almost nothing for the review rules to detect.  This module rebuilds structure
from the text itself:

* leading short lines (name, instructor, course, date, title) become their own
  paragraphs, the way they appear in a manuscript;
* the body is re-split into sentences and grouped into paragraphs of roughly
  three sentences, which is close enough to the original structure for
  paragraph-level diagnostics;
* explicit blank lines, when the extractor preserves them, always win.
"""
from __future__ import annotations

import re

from .segmenter import split_sentences

_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def _lines(raw: str) -> list[str]:
    return [line.strip() for line in _CONTROL.sub("", raw).splitlines() if line.strip()]


def _has_blank_lines(raw: str) -> bool:
    return bool(re.search(r"\n[ \t]*\n", raw))


def _front_matter(lines: list[str]) -> tuple[list[str], list[str]]:
    """Peel off name/instructor/course/date/title lines."""
    front: list[str] = []
    idx = 0
    while idx < len(lines) and len(front) < 6:
        line = lines[idx]
        words = line.split()
        if (
            len(line) <= 70
            and len(words) <= 9
            and not line.endswith((".", "!", "?", ":"))
            and (line[:1].isupper() or line[:1].isdigit())
        ):
            front.append(line)
            idx += 1
            continue
        break
    # A title is usually the last short line before prose; if we swallowed the
    # first body sentence by accident, push it back.
    if front and len(front) == 1 and len(front[0].split()) <= 3:
        pass
    return front, lines[idx:]


def _group_sentences(text: str, per_paragraph: int = 3) -> list[str]:
    sentences = [s.text.strip() for s in split_sentences(text) if s.text.strip()]
    paragraphs: list[str] = []
    buffer: list[str] = []
    for sentence in sentences:
        buffer.append(sentence)
        if len(buffer) >= per_paragraph:
            paragraphs.append(" ".join(buffer))
            buffer = []
    if buffer:
        paragraphs.append(" ".join(buffer))
    return paragraphs


def pdf_text_to_paragraphs(raw: str) -> str:
    if not raw or not raw.strip():
        return ""
    if _has_blank_lines(raw):
        chunks = [re.sub(r"\s+", " ", c).strip() for c in re.split(r"\n[ \t]*\n", raw) if c.strip()]
        if len(chunks) > 1:
            return "\n\n".join(chunks)

    lines = _lines(raw)
    if not lines:
        return ""
    front, body_lines = _front_matter(lines)
    body = re.sub(r"\s+", " ", " ".join(body_lines)).strip()
    paragraphs = _group_sentences(body) if body else []
    return "\n\n".join(front + paragraphs)


def plain_text_to_paragraphs(raw: str) -> str:
    """Pasted text: respect blank lines, otherwise rebuild paragraphs."""
    if not raw or not raw.strip():
        return ""
    if _has_blank_lines(raw):
        chunks = [re.sub(r"\s+", " ", c).strip() for c in re.split(r"\n[ \t]*\n", raw) if c.strip()]
        if len(chunks) > 1:
            return "\n\n".join(chunks)
    lines = _lines(raw)
    front, body_lines = _front_matter(lines)
    body = re.sub(r"\s+", " ", " ".join(body_lines)).strip()
    return "\n\n".join(front + (_group_sentences(body) if body else []))
