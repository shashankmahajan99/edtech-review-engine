"""Separate a confidently recognized previous review letter from student prose."""
from __future__ import annotations

import re
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_SIGNOFF = re.compile(r"^(?:best wishes|best regards|regards|sincerely|warm regards|all the best)[,.]?(?:\s+\S.*)?$", re.I)
_GREETING = re.compile(r"^(?:dear|hi|hello)\s+\S+", re.I)
_FEEDBACK = re.compile(r"you have done (?:a )?(?:pretty )?(?:good|decent|great|nice) job|there are (?:a few|some) areas|your next draft|reading the revised draft|as you revise", re.I)


def previous_letter_start(paragraphs) -> int | None:
    """Return a paragraph index only with both a sign-off and reviewer language.

    A student's letter or essay mentioning revisions is not enough. This helper
    does not inspect or reuse previous margin feedback to generate a new review.
    """
    nonempty = [p for p in paragraphs if p.text.strip()]
    for end in range(len(nonempty) - 1, -1, -1):
        if not _SIGNOFF.match(nonempty[end].normalized):
            continue
        window = nonempty[max(0, end - 30):end]
        starts = [i for i, p in enumerate(window) if _GREETING.match(p.normalized)
                  or re.match(r"^you have done|^thank you for (?:submitting|sharing)", p.normalized, re.I)]
        for start in starts:
            candidate = window[start:]
            prose = " ".join(p.normalized for p in candidate)
            if len(_FEEDBACK.findall(prose)) >= 2:
                return candidate[0].index
    return None


def remove_previous_letter(source: str | Path, target: str | Path) -> dict:
    """Write a separate clean package; preserve all student text and package parts."""
    from .docmodel import load_document

    source, target = Path(source), Path(target)
    if source.resolve() == target.resolve():
        raise ValueError("review material must be removed into a separate file")
    model = load_document(str(source))
    start = previous_letter_start(model.paragraphs)
    if start is None:
        return {"removed": False, "paragraphs": 0}
    first = next(p for p in model.paragraphs if p.index == start)
    if first.element.getparent().tag != f"{W}body":
        return {"removed": False, "paragraphs": 0}
    body = model.doc.element.body
    removed = 0
    for node in list(body)[body.index(first.element):]:
        if node.tag != f"{W}sectPr":
            removed += len(list(node.iter(f"{W}p")))
            body.remove(node)
    document_xml = etree.tostring(model.doc.element, xml_declaration=True, encoding="utf-8", standalone=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(source) as before, ZipFile(target, "w", ZIP_DEFLATED) as after:
        for item in before.infolist():
            after.writestr(item, document_xml if item.filename == "word/document.xml" else before.read(item.filename))
    return {"removed": True, "paragraphs": removed}
