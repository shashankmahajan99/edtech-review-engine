"""OpenXML writer for the ThinkingStorm deliverable.

Produces a real .docx with:

* native Word comments anchored to the exact quoted sentence (run splitting so
  the highlight covers only the quoted words),
* one clickable knowledge-base link per labelled comment,
* a native endnote letter in ``word/endnotes.xml`` in red Times New Roman 12 pt
  at double spacing, matching the reviewer's exemplars,
* every package part and relationship Word needs to open the file cleanly.

The original manuscript is never edited: text nodes are only *split*, never
rewritten, and the concatenated text of every paragraph is verified unchanged
by :mod:`engine.review.validate` before a deliverable is released.
"""
from __future__ import annotations

import copy
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from lxml import etree

from .docmodel import DocumentModel, W_NS

R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
TYPES_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
XML_SPACE = "{http://www.w3.org/XML/1998/namespace}space"

W = f"{{{W_NS}}}"
R = f"{{{R_NS}}}"
REL = f"{{{PKG_REL_NS}}}"
CT = f"{{{TYPES_NS}}}"

COMMENT_PART = "word/comments.xml"
COMMENT_RELS = "word/_rels/comments.xml.rels"
ENDNOTE_PART = "word/endnotes.xml"
DOC_PART = "word/document.xml"
DOC_RELS = "word/_rels/document.xml.rels"
CONTENT_TYPES = "[Content_Types].xml"
STYLES_PART = "word/styles.xml"

COMMENT_TEXT_STYLE = {"type": "paragraph", "styleId": "CommentText", "name": "Comment Text"}
COMMENT_REF_STYLE = {"type": "character", "styleId": "CommentReference", "name": "Comment Reference"}
HYPERLINK_STYLE = {"type": "character", "styleId": "Hyperlink", "name": "Hyperlink"}
ENDNOTE_TEXT_STYLE = {"type": "paragraph", "styleId": "EndnoteText", "name": "Endnote Text"}
ENDNOTE_REF_STYLE = {"type": "character", "styleId": "EndnoteReference", "name": "Endnote Reference"}


@dataclass
class WriteResult:
    path: str
    comment_ids: list[str]


# ---------------------------------------------------------------------------
# paragraph anchoring
# ---------------------------------------------------------------------------

def _top_level_unit(run):
    """Return the top-level child of the paragraph that contains ``run``."""
    node = run
    while node is not None and node.getparent() is not None:
        parent = node.getparent()
        if parent.tag == f"{W}p":
            return node
        node = parent
    return None


def _rewalk(paragraph_element) -> list[tuple]:
    """Return (t_element, run, unit, start, end, text) in document order."""
    from .docmodel import _walk_text_tokens, _CHAR_TOKENS

    out = []
    pos = 0
    for kind, el, run, unit in _walk_text_tokens(paragraph_element):
        txt = (el.text or "") if kind == "t" else _CHAR_TOKENS.get(el.tag, "")
        if not txt:
            continue
        out.append((el, run, unit, pos, pos + len(txt), txt))
        pos += len(txt)
    return out


_NO_EXPLODE = {f"{W}drawing", f"{W}object", f"{W}fldChar", f"{W}instrText",
               f"{W}pict", f"{W}footnoteReference", f"{W}endnoteReference"}


def explode_runs(paragraph_element) -> int:
    """Give every text token its own run so it can be split for anchoring.

    Rendering is unchanged: each new run copies the original run properties.
    Returns the number of runs rewritten.
    """
    changed = 0
    runs = [r for r in paragraph_element.iter(f"{W}r")]
    for run in runs:
        if run.getparent() is None:
            continue
        if any(child.tag in _NO_EXPLODE for child in run):
            continue
        children = [c for c in run if c.tag != f"{W}rPr"]
        if len(children) <= 1:
            continue
        rpr = run.find(f"{W}rPr")
        parent = run.getparent()
        idx = parent.index(run)
        new_runs = []
        for child in children:
            new_run = etree.Element(f"{W}r")
            if rpr is not None:
                new_run.append(copy.deepcopy(rpr))
            new_run.append(child)
            new_runs.append(new_run)
        parent[idx:idx + 1] = new_runs
        changed += 1
    return changed


def _run_is_splittable(run) -> bool:
    if run is None:
        return False
    texts = run.findall(f"{W}t")
    if len(texts) != 1:
        return False
    for child in run:
        if child.tag not in {f"{W}rPr", f"{W}t"}:
            return False
    return True


def normalize_span(paragraph_element, start: int, end: int) -> tuple[int, int]:
    """Widen a span so it never starts or ends inside a nested container."""
    nodes = _rewalk(paragraph_element)
    if not nodes:
        return start, end
    total = nodes[-1][4]
    start = max(0, min(start, total))
    end = max(start, min(end, total))
    touched = [n for n in nodes if n[3] < end and n[4] > start]
    nested_units = [n[2] for n in touched if n[1] is not n[2]]
    if not nested_units:
        return start, end
    unit_ids = {id(u) for u in nested_units}
    for n in nodes:
        if id(n[2]) in unit_ids:
            start = min(start, n[3])
            end = max(end, n[4])
    return start, end


def can_anchor(paragraph_element, start: int, end: int) -> bool:
    """True when [start, end) can be anchored after span normalisation."""
    start, end = normalize_span(paragraph_element, start, end)
    nodes = _rewalk(paragraph_element)
    if not nodes:
        return False
    touched = [n for n in nodes if n[3] < end and n[4] > start]
    if not touched:
        return False
    for t_el, run, unit, n_start, n_end, text in touched:
        if run is not unit:
            # nested container: must be covered entirely
            unit_nodes = [n for n in nodes if n[2] is unit]
            if unit_nodes and (start > unit_nodes[0][3] or end < unit_nodes[-1][4]):
                return False
        elif not _run_is_splittable(run):
            return False
    return True


def anchor_comment(paragraph_element, start: int, end: int, cid: int) -> bool:
    """Insert commentRangeStart/End + reference around [start, end).

    Paragraph text is preserved exactly; runs are only split.
    """
    start, end = normalize_span(paragraph_element, start, end)
    nodes = _rewalk(paragraph_element)
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

    runs_to_split: dict[object, dict] = {}
    covered_units: set[int] = set()
    for t_el, run, unit, n_start, n_end, text in touched:
        if run is not unit:
            unit_nodes = [n for n in nodes if n[2] is unit]
            if unit_nodes and (start > unit_nodes[0][3] or end < unit_nodes[-1][4]):
                return False
            covered_units.add(id(unit))
            continue
        if not _run_is_splittable(run):
            return False
        entry = runs_to_split.setdefault(run, {"run_start": n_start, "cuts": set()})
        if n_start < start < n_end:
            entry["cuts"].add(start - n_start)
        if n_start < end < n_end:
            entry["cuts"].add(end - n_start)

    cid_str = str(cid)
    new_children: list = []
    started = False
    ended = False

    def _insert_end() -> None:
        nonlocal ended
        new_children.append(_marker("commentRangeEnd", cid_str))
        ref_run = etree.Element(f"{W}r")
        rpr = etree.SubElement(ref_run, f"{W}rPr")
        style = etree.SubElement(rpr, f"{W}rStyle")
        style.set(f"{W}val", "CommentReference")
        ref = etree.SubElement(ref_run, f"{W}commentReference")
        ref.set(f"{W}id", cid_str)
        new_children.append(ref_run)
        ended = True

    for child in list(paragraph_element):
        if id(child) in covered_units:
            unit_nodes = [n for n in nodes if n[2] is child]
            if unit_nodes and unit_nodes[0][3] == start and not started:
                new_children.append(_marker("commentRangeStart", cid_str))
                started = True
            new_children.append(child)
            if unit_nodes and unit_nodes[-1][4] == end and not ended:
                _insert_end()
            continue

        if child not in runs_to_split:
            new_children.append(child)
            continue

        text = child.find(f"{W}t").text or ""
        entry = runs_to_split[child]
        base = entry["run_start"]
        segs: list[tuple[int, int]] = []
        prev = 0
        for b in sorted(entry["cuts"]):
            segs.append((prev, b))
            prev = b
        segs.append((prev, len(text)))

        for a, b in segs:
            if a == b:
                continue
            clone = copy.deepcopy(child)
            t = clone.find(f"{W}t")
            t.text = text[a:b]
            t.set(XML_SPACE, "preserve")
            if base + a == start and not started:
                new_children.append(_marker("commentRangeStart", cid_str))
                started = True
            new_children.append(clone)
            if base + b == end and not ended:
                _insert_end()

    if not (started and ended):
        return False

    paragraph_element[:] = new_children
    return True


def _marker(tag: str, cid_str: str):
    marker = etree.Element(f"{W}{tag}")
    marker.set(f"{W}id", cid_str)
    return marker


# ---------------------------------------------------------------------------
# comments part
# ---------------------------------------------------------------------------

def _comment_element(cid: int, author: str, initials: str, date: str,
                     category: str | None, body: str, rel_id: str | None):
    c = etree.Element(f"{W}comment")
    c.set(f"{W}id", str(cid))
    c.set(f"{W}author", author)
    c.set(f"{W}date", date)
    c.set(f"{W}initials", initials)

    p = etree.SubElement(c, f"{W}p")
    ppr = etree.SubElement(p, f"{W}pPr")
    pstyle = etree.SubElement(ppr, f"{W}pStyle")
    pstyle.set(f"{W}val", "CommentText")

    ref_run = etree.SubElement(p, f"{W}r")
    rpr = etree.SubElement(ref_run, f"{W}rPr")
    rstyle = etree.SubElement(rpr, f"{W}rStyle")
    rstyle.set(f"{W}val", "CommentReference")
    etree.SubElement(ref_run, f"{W}annotationRef")

    if category and rel_id:
        link = etree.SubElement(p, f"{W}hyperlink")
        link.set(f"{R}id", rel_id)
        link.set(f"{W}history", "1")
        lr = etree.SubElement(link, f"{W}r")
        lrpr = etree.SubElement(lr, f"{W}rPr")
        lstyle = etree.SubElement(lrpr, f"{W}rStyle")
        lstyle.set(f"{W}val", "Hyperlink")
        color = etree.SubElement(lrpr, f"{W}color")
        color.set(f"{W}val", "0563C1")
        u = etree.SubElement(lrpr, f"{W}u")
        u.set(f"{W}val", "single")
        t = etree.SubElement(lr, f"{W}t")
        t.set(XML_SPACE, "preserve")
        t.text = category

    body_run = etree.SubElement(p, f"{W}r")
    bt = etree.SubElement(body_run, f"{W}t")
    bt.set(XML_SPACE, "preserve")
    bt.text = (" " + body) if category else body
    return c


def _load_or_create(path: Path, root_tag: str):
    if path.exists():
        try:
            tree = etree.parse(str(path))
            return tree, tree.getroot()
        except etree.XMLSyntaxError:
            pass
    root = etree.Element(f"{W}{root_tag}", nsmap={"w": W_NS, "r": R_NS})
    return etree.ElementTree(root), root


def _existing_comment_ids(root) -> list[int]:
    ids = []
    for c in root.findall(f"{W}comment"):
        try:
            ids.append(int(c.get(f"{W}id")))
        except (TypeError, ValueError):
            continue
    return ids


# ---------------------------------------------------------------------------
# endnotes part
# ---------------------------------------------------------------------------

def _endnote_paragraph(text: str, first: bool, bold: bool):
    p = etree.Element(f"{W}p")
    ppr = etree.SubElement(p, f"{W}pPr")
    pstyle = etree.SubElement(ppr, f"{W}pStyle")
    pstyle.set(f"{W}val", "EndnoteText")
    spacing = etree.SubElement(ppr, f"{W}spacing")
    spacing.set(f"{W}line", "480")
    spacing.set(f"{W}lineRule", "auto")

    run = etree.SubElement(p, f"{W}r")
    rpr = etree.SubElement(run, f"{W}rPr")
    fonts = etree.SubElement(rpr, f"{W}rFonts")
    for attr in ("ascii", "hAnsi", "cs"):
        fonts.set(f"{W}{attr}", "Times New Roman")
    color = etree.SubElement(rpr, f"{W}color")
    color.set(f"{W}val", "FF0000")
    sz = etree.SubElement(rpr, f"{W}sz")
    sz.set(f"{W}val", "24")
    szcs = etree.SubElement(rpr, f"{W}szCs")
    szcs.set(f"{W}val", "24")
    if bold:
        etree.SubElement(rpr, f"{W}b")
        etree.SubElement(rpr, f"{W}bCs")

    if first:
        ref = etree.SubElement(run, f"{W}endnoteRef")

    t = etree.SubElement(run, f"{W}t")
    t.set(XML_SPACE, "preserve")
    t.text = (" " + text) if first else text
    return p


def _build_endnotes(root, paragraphs: list[str], reviewer_name: str):
    for en in list(root.findall(f"{W}endnote")):
        if en.get(f"{W}id") == "1":
            root.remove(en)

    if not any(en.get(f"{W}id") == "-1" for en in root.findall(f"{W}endnote")):
        sep = etree.SubElement(root, f"{W}endnote")
        sep.set(f"{W}id", "-1")
        sep.set(f"{W}type", "separator")
        sp = etree.SubElement(sep, f"{W}p")
        sr = etree.SubElement(sp, f"{W}r")
        etree.SubElement(sr, f"{W}separator")

    if not any(en.get(f"{W}id") == "0" for en in root.findall(f"{W}endnote")):
        cont = etree.SubElement(root, f"{W}endnote")
        cont.set(f"{W}id", "0")
        cont.set(f"{W}type", "continuationSeparator")
        cp = etree.SubElement(cont, f"{W}p")
        cr = etree.SubElement(cp, f"{W}r")
        etree.SubElement(cr, f"{W}continuationSeparator")

    en1 = etree.SubElement(root, f"{W}endnote")
    en1.set(f"{W}id", "1")

    for idx, text in enumerate(paragraphs):
        bold = (
            idx == 0
            or text.endswith(":")
            or text.strip().lower() == reviewer_name.lower()
            or text.startswith("Dear ")
        )
        en1.append(_endnote_paragraph(text, first=(idx == 0), bold=bold))


def _ensure_endnote_reference(model: DocumentModel):
    body = model.doc.element.body
    if body.find(f".//{W}endnoteReference") is not None:
        return
    p = etree.SubElement(body, f"{W}p")
    run = etree.SubElement(p, f"{W}r")
    rpr = etree.SubElement(run, f"{W}rPr")
    style = etree.SubElement(rpr, f"{W}rStyle")
    style.set(f"{W}val", "EndnoteReference")
    ref = etree.SubElement(run, f"{W}endnoteReference")
    ref.set(f"{W}id", "1")


# ---------------------------------------------------------------------------
# package plumbing
# ---------------------------------------------------------------------------

def _ensure_rel(root, rel_id: str, rel_type: str, target: str, external: bool = False):
    for rel in root.findall(f"{REL}Relationship"):
        if rel.get("Id") == rel_id:
            return
    rel = etree.SubElement(root, f"{REL}Relationship")
    rel.set("Id", rel_id)
    rel.set("Type", rel_type)
    rel.set("Target", target)
    if external:
        rel.set("TargetMode", "External")


def _ensure_override(root, part: str, content_type: str):
    for o in root.findall(f"{CT}Override"):
        if o.get("PartName") == part:
            return
    o = etree.SubElement(root, f"{CT}Override")
    o.set("PartName", part)
    o.set("ContentType", content_type)


def _ensure_style(root, spec: dict):
    styles = root.findall(f"{W}style")
    if any(s.get(f"{W}styleId") == spec["styleId"] for s in styles):
        return
    style = etree.SubElement(root, f"{W}style")
    style.set(f"{W}type", spec["type"])
    style.set(f"{W}styleId", spec["styleId"])
    name = etree.SubElement(style, f"{W}name")
    name.set(f"{W}val", spec["name"])
    if spec["type"] == "paragraph":
        ppr = etree.SubElement(style, f"{W}pPr")
        spacing = etree.SubElement(ppr, f"{W}spacing")
        spacing.set(f"{W}after", "0")
    else:
        rpr = etree.SubElement(style, f"{W}rPr")
        if spec["styleId"] == "Hyperlink":
            color = etree.SubElement(rpr, f"{W}color")
            color.set(f"{W}val", "0563C1")
            u = etree.SubElement(rpr, f"{W}u")
            u.set(f"{W}val", "single")


def _write_zip(source: str, destination: str, replacements: dict[str, bytes],
               additions: dict[str, bytes]):
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(source) as src:
            names = src.namelist()
            for name in names:
                if name in replacements:
                    continue
                target = tmp_dir / name
                target.parent.mkdir(parents=True, exist_ok=True)
                with open(target, "wb") as fh:
                    fh.write(src.read(name))
        for name, data in replacements.items():
            target = tmp_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        for name, data in additions.items():
            if name in names:
                continue
            target = tmp_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)

        out = Path(destination)
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.exists():
            out.unlink()
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
            # [Content_Types].xml must be first per OPC convention
            ordered = sorted(
                (p for p in tmp_dir.rglob("*") if p.is_file()),
                key=lambda p: (p.name != "[Content_Types].xml", str(p)),
            )
            for path in ordered:
                z.write(path, path.relative_to(tmp_dir).as_posix())
        return str(out)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def write_deliverable(
    model: DocumentModel,
    composed: list[tuple],
    endnote_paragraphs: list[str],
    output_path: str,
    reviewer_name: str = "Raunak Banga",
    reviewer_initials: str = "RB",
) -> "WriteResult":
    """Anchor every comment and write the final .docx.

    ``composed`` is a list of (SelectedComment, body_text) tuples in document
    order.  ``endnote_paragraphs`` is the letter body including greeting and
    signature.  Returns the written path plus the comment ids that were assigned
    (existing comments in the file keep their ids).
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    source = model.path

    # Work on the in-memory python-docx tree so element identity is preserved.
    paragraph_by_index = {p.index: p for p in model.paragraphs}

    # 1. existing comments part (append, never clobber)
    tmp_dir = Path(tempfile.mkdtemp())
    try:
        with zipfile.ZipFile(source) as z:
            exists_comments = COMMENT_PART in z.namelist()
            comments_bytes = z.read(COMMENT_PART) if exists_comments else None
            exists_rels = COMMENT_RELS in z.namelist()
            rels_bytes = z.read(COMMENT_RELS) if exists_rels else None
            exists_endnotes = ENDNOTE_PART in z.namelist()
            endnotes_bytes = z.read(ENDNOTE_PART) if exists_endnotes else None
            styles_bytes = z.read(STYLES_PART) if STYLES_PART in z.namelist() else None
            ct_root = etree.fromstring(z.read(CONTENT_TYPES))
            doc_rels_root = etree.fromstring(z.read(DOC_RELS))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if comments_bytes:
        c_root = etree.fromstring(comments_bytes)
    else:
        c_root = etree.Element(f"{W}comments", nsmap={"w": W_NS, "r": R_NS})
    existing_ids = _existing_comment_ids(c_root)
    next_id = (max(existing_ids) + 1) if existing_ids else 0

    if rels_bytes:
        crels_root = etree.fromstring(rels_bytes)
    else:
        crels_root = etree.Element(f"{REL}Relationships", nsmap={None: PKG_REL_NS})

    # 2. anchor + build comment nodes
    failures: list[str] = []
    assigned: list[str] = []
    for item, body in composed:
        finding = item.finding
        para = paragraph_by_index.get(finding.paragraph.index)
        if para is None:
            failures.append(f"missing paragraph {finding.paragraph.index}")
            continue
        cid = next_id
        if not anchor_comment(para.element, finding.start, finding.end, cid):
            failures.append(f"anchor failed p{finding.paragraph.index} {finding.start}-{finding.end}")
            continue
        next_id += 1
        assigned.append(str(cid))

        rel_id = None
        category = item.category if item.labelled else None
        if category:
            rel_id = f"rIdTsLink{cid}"
            from .links import link_for
            _ensure_rel(crels_root, rel_id,
                        "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink",
                        link_for(category, model), external=True)
        c_root.append(_comment_element(
            cid, reviewer_name, reviewer_initials, now, category, body, rel_id
        ))

    if failures:
        raise RuntimeError("anchoring failed: " + "; ".join(failures))

    # 3. endnotes
    if endnotes_bytes:
        en_root = etree.fromstring(endnotes_bytes)
    else:
        en_root = etree.Element(f"{W}endnotes", nsmap={"w": W_NS})
    _build_endnotes(en_root, endnote_paragraphs, reviewer_name)
    _ensure_endnote_reference(model)

    # 4. styles
    if styles_bytes:
        st_root = etree.fromstring(styles_bytes)
    else:
        st_root = etree.Element(f"{W}styles", nsmap={"w": W_NS})
    for spec in (COMMENT_TEXT_STYLE, COMMENT_REF_STYLE, HYPERLINK_STYLE,
                 ENDNOTE_TEXT_STYLE, ENDNOTE_REF_STYLE):
        _ensure_style(st_root, spec)

    # 5. package plumbing
    _ensure_override(ct_root, "/word/comments.xml",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.comments+xml")
    _ensure_override(ct_root, "/word/endnotes.xml",
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.endnotes+xml")
    _ensure_rel(doc_rels_root, "rIdTsComments",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/comments",
                "comments.xml")
    _ensure_rel(doc_rels_root, "rIdTsEndnotes",
                "http://schemas.openxmlformats.org/officeDocument/2006/relationships/endnotes",
                "endnotes.xml")

    def _ser(root) -> bytes:
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)

    replacements = {
        DOC_PART: _ser(model.doc.element),
        COMMENT_PART: _ser(c_root),
        COMMENT_RELS: _ser(crels_root),
        ENDNOTE_PART: _ser(en_root),
        STYLES_PART: _ser(st_root),
        DOC_RELS: _ser(doc_rels_root),
        CONTENT_TYPES: _ser(ct_root),
    }
    written = _write_zip(source, output_path, replacements, {})
    return WriteResult(path=written, comment_ids=assigned)
