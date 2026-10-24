"""Format-preserving tracked changes.

The legacy redliner rebuilt each edited paragraph from plain text, which threw
away bold/italic runs, images, tabs and anything python-docx does not surface as
paragraph text (revision marks, text boxes).  This module edits the OpenXML
directly:

* the package is copied entry-for-entry; only ``word/document.xml`` changes,
* only the target span is split out of its runs,
* that span becomes ``<w:del>`` and the replacement ``<w:ins>``,
* every other run, image, table, header and style stays exactly as it was.

If an edit cannot be isolated safely (it crosses a hyperlink or a non-text
element), it is skipped rather than guessed at.
"""
from __future__ import annotations

import copy
import shutil
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
W = f"{{{W_NS}}}"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"
DOC_PART = "word/document.xml"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nodes(paragraph) -> list[tuple]:
    """(t, run, unit, start, end, text) for every text token in a paragraph."""
    from .writer import _rewalk

    return _rewalk(paragraph)


def _simple_run(run) -> bool:
    if run is None:
        return False
    texts = run.findall(f"{W}t")
    if len(texts) != 1:
        return False
    return all(child.tag in {f"{W}rPr", f"{W}t"} for child in run)


def _apply_span(paragraph, start: int, end: int, replacement: str,
                author: str, change_id: int) -> bool:
    nodes = _nodes(paragraph)
    if not nodes:
        return False
    total = nodes[-1][4]
    start = max(0, min(start, total))
    end = max(start, min(end, total))
    if end <= start:
        return False

    touched = [n for n in nodes if n[3] < end and n[4] > start]
    if not touched:
        return False
    for _t, run, unit, *_rest in touched:
        if run is not unit or not _simple_run(run):
            return False

    # safety: no structural element may sit between the first and last run
    children = list(paragraph)
    try:
        first_idx = children.index(touched[0][1])
        last_idx = children.index(touched[-1][1])
    except ValueError:
        return False
    between = children[first_idx:last_idx + 1]
    if any(not (child.tag == f"{W}r" and _simple_run(child)) for child in between):
        return False

    changes: list = []
    inserted = False
    del_elem = None
    first_run = touched[0][1]

    for child in children:
        if child.tag != f"{W}r" or child not in between:
            changes.append(child)
            continue
        text = child.find(f"{W}t").text or ""
        run_start = next(n[3] for n in nodes if n[1] is child)
        run_end = run_start + len(text)

        cuts = []
        if run_start < start < run_end:
            cuts.append(start - run_start)
        if run_start < end < run_end:
            cuts.append(end - run_start)
        cuts = sorted(set(cuts))

        segments = []
        prev = 0
        for cut in cuts:
            segments.append((prev, cut))
            prev = cut
        segments.append((prev, len(text)))

        for a, b in segments:
            if a == b:
                continue
            clone = copy.deepcopy(child)
            t = clone.find(f"{W}t")
            t.text = text[a:b]
            t.set(XML_SPACE, "preserve")
            g_start, g_end = run_start + a, run_start + b
            inside = g_start >= start and g_end <= end
            if inside:
                if del_elem is None:
                    del_elem = etree.Element(f"{W}del")
                    del_elem.set(f"{W}id", str(change_id))
                    del_elem.set(f"{W}author", author)
                    del_elem.set(f"{W}date", _now())
                    changes.append(del_elem)
                # deleted text must live in w:delText
                for node in list(clone):
                    if node.tag == f"{W}t":
                        node.tag = f"{W}delText"
                del_elem.append(clone)
                if g_end == end and not inserted:
                    changes.append(_insertion(replacement, first_run, author, change_id))
                    inserted = True
            else:
                if del_elem is not None and not inserted:
                    changes.append(_insertion(replacement, first_run, author, change_id))
                    inserted = True
                changes.append(clone)

    if del_elem is None:
        return False
    if not inserted:
        changes.append(_insertion(replacement, first_run, author, change_id))

    paragraph[:] = changes
    return True


def _insertion(replacement: str, first_run, author: str, change_id: int):
    ins = etree.Element(f"{W}ins")
    ins.set(f"{W}id", str(change_id))
    ins.set(f"{W}author", author)
    ins.set(f"{W}date", _now())
    run = etree.SubElement(ins, f"{W}r")
    rpr = first_run.find(f"{W}rPr")
    if rpr is not None:
        run.append(copy.deepcopy(rpr))
    t = etree.SubElement(run, f"{W}t")
    t.set(XML_SPACE, "preserve")
    t.text = replacement
    return ins


def _paragraph_text(paragraph) -> str:
    return "".join(node[5] for node in _nodes(paragraph))


def apply_line_edits(input_path: str, output_path: str, edits: list[dict],
                     author: str = "Apex Admissions Editorial Desk") -> int:
    """Apply edits to a copy of the document; return how many were applied."""
    source = Path(input_path)
    tmp_dir = Path(tempfile.mkdtemp())
    applied = 0
    change_counter = 1
    try:
        with zipfile.ZipFile(source) as z:
            names = z.namelist()
            for name in names:
                if name == DOC_PART:
                    continue
                target = tmp_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(z.read(name))
            root = etree.fromstring(z.read(DOC_PART))

        paragraphs = list(root.iter(f"{W}p"))
        for edit in edits:
            original = (edit.get("original_text") or "").strip()
            replacement = edit.get("suggested_replacement") or ""
            if not original or not replacement or original == replacement:
                continue
            for paragraph in paragraphs:
                text = _paragraph_text(paragraph)
                if original not in text:
                    continue
                # apply from the end so earlier offsets stay valid
                position = text.rfind(original)
                if _apply_span(paragraph, position, position + len(original),
                               replacement, author, change_counter):
                    applied += 1
                    change_counter += 1
                    break

        target = tmp_dir / DOC_PART
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                          standalone=True))

        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            ordered = sorted(
                (p for p in tmp_dir.rglob("*") if p.is_file()),
                key=lambda p: (p.name != "[Content_Types].xml", str(p)),
            )
            for path in ordered:
                z.write(path, path.relative_to(tmp_dir).as_posix())
        return applied
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
