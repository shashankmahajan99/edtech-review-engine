"""Release gate for ThinkingStorm deliverables.

A deliverable is only handed to a student when every check below passes.  The
gate re-opens the produced .docx and inspects the XML independently of the
writer, so a bug in the writer cannot certify itself.
"""
from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from docx import Document
from lxml import etree

from . import links
from .docmodel import W_NS, DocumentModel
from .style_guard import check_text_block, banned_hits

W = f"{{{W_NS}}}"
R = f"{{{('http://schemas.openxmlformats.org/officeDocument/2006/relationships')}}}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"


@dataclass
class ValidationReport:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)


def _comment_body(comment) -> str:
    """Comment text excluding the clickable category label."""
    parts: list[str] = []
    for t in comment.iter(f"{W}t"):
        node = t.getparent()
        inside_link = False
        while node is not None and node is not comment:
            if node.tag == f"{W}hyperlink":
                inside_link = True
                break
            node = node.getparent()
        if not inside_link:
            parts.append(t.text or "")
    return "".join(parts).strip()


def _paragraph_texts(root) -> list[str]:
    return ["".join(t.text or "" for t in p.iter(f"{W}t")) for p in root.iter(f"{W}p")]


def _body_texts(doc) -> list[str]:
    """Walk the produced body with the same text rules as the document model."""
    from .docmodel import build_paragraph

    texts: list[str] = []
    idx = 0
    for child in doc.element.body.iterchildren():
        if child.tag == f"{W}p":
            texts.append(build_paragraph(child, idx).text)
            idx += 1
        elif child.tag == f"{W}tbl":
            for p_el in child.iter(f"{W}p"):
                texts.append(build_paragraph(p_el, idx).text)
                idx += 1
    return texts


def _anchors(document_root) -> dict[str, list[tuple[int, int, str]]]:
    """Map comment id -> list of (start index, end index, text)."""
    out: dict[str, list[tuple[int, int, str]]] = {}
    for p in document_root.iter(f"{W}p"):
        open_ids: list[str] = []
        buffers: dict[str, list[str]] = {}
        for el in p.iter():
            if el.tag == f"{W}commentRangeStart":
                cid = el.get(f"{W}id")
                open_ids.append(cid)
                buffers[cid] = []
            elif el.tag == f"{W}commentRangeEnd":
                cid = el.get(f"{W}id")
                if cid in open_ids:
                    open_ids.remove(cid)
                    out.setdefault(cid, []).append((0, 0, "".join(buffers.get(cid, []))))
            elif el.tag == f"{W}t":
                for cid in open_ids:
                    buffers.setdefault(cid, []).append(el.text or "")
    return out


def validate_deliverable(
    output_path: str,
    model: DocumentModel,
    expected: list[tuple[str, str]],  # (comment_id, expected quote)
    comment_bodies: list[str],
    endnote_paragraphs: list[str],
    reviewer_name: str = "Raunak Banga",
) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict = {}
    path = Path(output_path)

    if not path.exists() or path.stat().st_size < 2000:
        return ValidationReport(False, ["output file missing or empty"], [], {})

    # -- opens as a docx ----------------------------------------------------
    try:
        Document(str(path))
    except Exception as exc:  # pragma: no cover - defensive
        errors.append(f"python-docx cannot open output: {exc}")

    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        for part in ("word/document.xml", "word/comments.xml", "word/endnotes.xml",
                     "word/_rels/comments.xml.rels", "[Content_Types].xml"):
            if part not in names:
                errors.append(f"missing package part {part}")
        if errors:
            return ValidationReport(False, errors, warnings, metrics)

        doc_root = etree.fromstring(z.read("word/document.xml"))
        c_root = etree.fromstring(z.read("word/comments.xml"))
        e_root = etree.fromstring(z.read("word/endnotes.xml"))
        rels_root = etree.fromstring(z.read("word/_rels/comments.xml.rels"))

    # -- original text preserved -------------------------------------------
    try:
        produced_doc = Document(str(path))
        produced_texts = _body_texts(produced_doc)
    except Exception:
        produced_texts = _paragraph_texts(doc_root)
    original_texts = [p.text for p in model.paragraphs]
    limit = min(len(original_texts), len(produced_texts))
    drift = [
        i for i in range(limit)
        if original_texts[i] != produced_texts[i]
    ]
    if drift:
        errors.append(f"manuscript text changed in {len(drift)} paragraph(s): {drift[:5]}")
    metrics["paragraphs"] = len(original_texts)

    # -- comments -----------------------------------------------------------
    comments = c_root.findall(f"{W}comment")
    ids = [c.get(f"{W}id") for c in comments]
    if len(ids) != len(set(ids)):
        errors.append("duplicate comment ids")

    anchors = _anchors(doc_root)
    expected_map = dict(expected)
    ours = set(expected_map)
    minimum = 3 if model.word_count < 300 else (4 if model.word_count < 600 else 5)
    if not (minimum <= len(ours) <= 22):
        errors.append(f"comment count {len(ours)} outside {minimum}-22")
    metrics["comments"] = len(ours)
    metrics["pre_existing_comments"] = len(ids) - len(ours)

    bodies_by_id = {}
    label_by_id = {}
    for c in comments:
        cid = c.get(f"{W}id")
        if cid not in ours:
            continue  # pre-existing reviewer notes are preserved untouched
        body = _comment_body(c)
        bodies_by_id[cid] = body
        links_in = [lk for lk in c.iter(f"{W}hyperlink")]
        if links_in:
            label_by_id[cid] = "".join(
                t.text or "" for t in links_in[0].iter(f"{W}t")
            ).strip().upper()
        if not body:
            errors.append(f"comment {cid}: empty body")
            continue
        words = len(body.split())
        if words < 6 or words > 95:
            errors.append(f"comment {cid}: {words} words outside 6-95")
        if not re.search(r"[.?!\"]$", body):
            errors.append(f"comment {cid}: does not end with terminal punctuation")
        if "  " in body:
            errors.append(f"comment {cid}: double space")
        hits = banned_hits(body)
        if hits:
            errors.append(f"comment {cid}: banned phrasing {hits}")
        label = label_by_id.get(cid)
        if label and body.upper().startswith(label + " "):
            errors.append(f"comment {cid}: body repeats its category label")

        got = anchors.get(cid, [])
        if len(got) != 1:
            errors.append(f"comment {cid}: expected 1 anchor, found {len(got)}")
            continue
        _s, _e, quoted = got[0]
        quoted_clean = re.sub(r"\s+", " ", quoted).strip()
        want = re.sub(r"\s+", " ", expected_map.get(cid, "")).strip()
        if want and quoted_clean != want:
            errors.append(
                f"comment {cid}: anchored text mismatch "
                f"({quoted_clean[:40]!r} != {want[:40]!r})"
            )

    # every range end needs a reference right after it
    for p in doc_root.iter(f"{W}p"):
        children = list(p)
        for i, child in enumerate(children):
            if child.tag == f"{W}commentRangeEnd":
                cid = child.get(f"{W}id")
                nxt = children[i + 1] if i + 1 < len(children) else None
                if nxt is None or nxt.tag != f"{W}r" or nxt.find(f"{W}commentReference") is None:
                    errors.append(f"comment {cid}: missing commentReference run")
                elif nxt.find(f"{W}commentReference").get(f"{W}id") != cid:
                    errors.append(f"comment {cid}: reference id mismatch")

    # overlapping ranges among *our* comments (pre-existing reviewer notes may
    # legitimately overlap when a second pass is appended)
    for p in doc_root.iter(f"{W}p"):
        active: list[str] = []
        for el in p.iter():
            if el.tag == f"{W}commentRangeStart":
                cid = el.get(f"{W}id")
                if cid in ours and any(a in ours for a in active):
                    errors.append("overlapping comment ranges in one paragraph")
                    break
                active.append(cid)
            elif el.tag == f"{W}commentRangeEnd":
                cid = el.get(f"{W}id")
                if cid in active:
                    active.remove(cid)

    # -- hyperlinks ---------------------------------------------------------
    rel_targets = {
        rel.get("Id"): rel.get("Target") for rel in rels_root.findall(f"{PKG}Relationship")
    }
    for c in comments:
        for link in c.iter(f"{W}hyperlink"):
            rid = link.get(f"{R}id")
            target = rel_targets.get(rid)
            if not target:
                errors.append(f"comment {c.get(f'{W}id')}: hyperlink {rid} has no relationship")
            elif not links.is_allowed(target):
                errors.append(f"comment {c.get(f'{W}id')}: disallowed link {target}")

    # -- endnote ------------------------------------------------------------
    en1 = next((en for en in e_root.findall(f"{W}endnote") if en.get(f"{W}id") == "1"), None)
    if en1 is None:
        errors.append("endnote id=1 missing")
    else:
        paras = ["".join(t.text or "" for t in p.iter(f"{W}t")) for p in en1.findall(f"{W}p")]
        joined = "\n".join(paras).strip()
        if not joined.lower().startswith("dear "):
            errors.append("endnote does not open with a greeting")
        if reviewer_name.lower() not in joined.lower():
            errors.append("endnote missing reviewer signature")
        domain_lines = [p for p in paras if p.strip().endswith(":")]
        if len(domain_lines) < 3:
            errors.append(f"endnote has {len(domain_lines)} domain headings, expected 3")
        if len(joined.split()) < 120:
            errors.append("endnote shorter than 120 words")
        # typography: TNR 12 pt red
        for run in en1.iter(f"{W}r"):
            t = run.find(f"{W}t")
            if t is None or not (t.text or "").strip():
                continue
            rpr = run.find(f"{W}rPr")
            if rpr is None:
                errors.append("endnote run missing rPr")
                continue
            fonts = rpr.find(f"{W}rFonts")
            color = rpr.find(f"{W}color")
            sz = rpr.find(f"{W}sz")
            if fonts is None or fonts.get(f"{W}ascii") != "Times New Roman":
                errors.append("endnote run not Times New Roman")
            if color is None or (color.get(f"{W}val") or "").upper() != "FF0000":
                errors.append("endnote run not red")
            if sz is None or sz.get(f"{W}val") != "24":
                errors.append("endnote run not 12 pt")
            if errors:
                break
        metrics["endnote_words"] = len(joined.split())

    # -- style guard --------------------------------------------------------
    bodies = [bodies_by_id[i] for i in ids if bodies_by_id.get(i)]
    report = check_text_block(bodies, "comments")
    metrics["style"] = report.metrics
    errors.extend(report.errors)

    en_text = " ".join(endnote_paragraphs[2:]) if len(endnote_paragraphs) > 2 else ""
    en_report = check_text_block([en_text], "endnote")
    metrics["endnote_style"] = en_report.metrics
    # A single long block cannot be judged for opener variety; keep substance checks.
    errors.extend(e for e in en_report.errors if "opener" not in e and "5-gram" not in e)

    return ValidationReport(ok=not errors, errors=errors, warnings=warnings, metrics=metrics)
