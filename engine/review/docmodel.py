"""Deterministic document model for the ThinkingStorm review pipeline.

The model exposes every body paragraph with a character-exact text stream and
an offset map back to the underlying ``w:t`` elements.  The very same walk is
used by the writer to place ``commentRangeStart`` / ``commentRangeEnd`` so an
anchored quote can never drift out of sync with the text a reviewer saw.

No network, no model calls, no randomness: parsing the same file always yields
the same model.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Iterator, Optional

from docx import Document
from docx.oxml.ns import qn

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
MC_NS = "http://schemas.openxmlformats.org/markup-compatibility/2006"


def w(tag: str) -> str:
    return f"{{{W_NS}}}{tag}"


# Subtrees that must never contribute text (duplicated fallbacks, text boxes).
_SKIP_SUBTREES = {w("txbxContent"), f"{{{MC_NS}}}Fallback"}

# Elements that render as text but are not ``w:t`` nodes.
_CHAR_TOKENS = {
    w("tab"): "\t",
    w("br"): "\n",
    w("cr"): "\n",
    w("noBreakHyphen"): "-",
    w("softHyphen"): "",
}


@dataclass
class TextNode:
    """A contiguous text token inside a paragraph."""

    element: object  # w:t / w:tab / w:br ...
    run: Optional[object]  # nearest w:r ancestor
    top_run: Optional[object]  # w:r whose parent is the paragraph (splittable)
    start: int  # offset in Paragraph.text
    end: int
    text: str


@dataclass
class Paragraph:
    index: int  # ordinal among body paragraphs (python-docx order)
    element: object  # w:p element
    text: str
    nodes: list[TextNode]
    style: str
    in_table: bool = False
    region: str = "body"  # front_matter | title | abstract | body | references
    is_heading: bool = False

    @property
    def words(self) -> list[str]:
        return self.text.split()

    @property
    def normalized(self) -> str:
        return re.sub(r"\s+", " ", self.text).strip()

    def slice_text(self, start: int, end: int) -> str:
        return self.text[start:end]


@dataclass
class DocumentModel:
    path: str
    paragraphs: list[Paragraph]
    doc: object
    fingerprint: str
    style: str = "mla"
    has_existing_comments: bool = False
    meta: dict = field(default_factory=dict)

    @property
    def body_paragraphs(self) -> list[Paragraph]:
        return [
            p for p in self.paragraphs
            if p.region == "body" and p.text.strip() and not p.is_heading
        ]

    @property
    def prose_paragraphs(self) -> list[Paragraph]:
        """Body paragraphs that carry real prose (>= 15 words)."""
        return [p for p in self.body_paragraphs if len(p.words) >= 15]

    @property
    def front_matter(self) -> list[Paragraph]:
        return [p for p in self.paragraphs if p.region == "front_matter"]

    @property
    def references(self) -> list[Paragraph]:
        return [p for p in self.paragraphs if p.region == "references"]

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.paragraphs if p.text.strip())

    @property
    def word_count(self) -> int:
        return sum(len(p.words) for p in self.paragraphs)


_CONTAINERS = {
    "hyperlink", "smartTag", "ins", "sdt", "sdtContent", "customXml", "fldSimple",
    "moveTo",
}


def _walk_text_tokens(paragraph_element) -> Iterator[tuple[str, object, object, Optional[object]]]:
    """Yield (kind, element, run, unit) in document order.

    ``unit`` is the top-level paragraph child that owns the token (the run
    itself, or the hyperlink/content-control wrapping it).  Paragraph and run
    properties (tab stops, borders, fonts) are never inspected as text.
    """

    def emit_run(run, unit):
        for child in run:
            if child.tag == w("t"):
                yield "t", child, run, unit
            elif child.tag in _CHAR_TOKENS:
                yield "char", child, run, unit

    def rec(el, unit):
        for child in el:
            tag = child.tag
            if not isinstance(tag, str):
                continue
            if tag == w("r"):
                yield from emit_run(child, unit if unit is not None else child)
            elif tag in {w(name) for name in _CONTAINERS}:
                yield from rec(child, child)

    yield from rec(paragraph_element, None)


def build_paragraph(element, index: int, in_table: bool = False) -> Paragraph:
    pieces: list[TextNode] = []
    pos = 0
    for kind, el, run, top_run in _walk_text_tokens(element):
        if kind == "t":
            txt = el.text or ""
        else:
            txt = _CHAR_TOKENS[el.tag]
        if not txt:
            continue
        pieces.append(TextNode(el, run, top_run, pos, pos + len(txt), txt))
        pos += len(txt)

    text = "".join(n.text for n in pieces)

    style = ""
    ppr = element.find(w("pPr"))
    if ppr is not None:
        pstyle = ppr.find(w("pStyle"))
        if pstyle is not None:
            style = pstyle.get(w("val")) or ""

    return Paragraph(
        index=index,
        element=element,
        text=text,
        nodes=pieces,
        style=style,
        in_table=in_table,
        is_heading=_looks_like_heading(text, style),
    )


def _looks_like_heading(text: str, style: str) -> bool:
    s = (style or "").lower()
    if s == "subtitle":
        return False
    if s == "title" or s.startswith("heading"):
        return True
    t = text.strip()
    if not t or len(t) > 90:
        return False
    words = t.split()
    if len(words) <= 8 and not t.endswith(".") and t[:1].isupper():
        # ALL-CAPS or Title-Case short line
        if t.isupper():
            return True
        cap = sum(1 for x in words if x[:1].isupper())
        if cap >= max(2, len(words) - 1):
            return True
    return False


_REF_HEADINGS = {
    "works cited", "work cited", "references", "reference list", "bibliography",
    "literature cited", "sources", "sources cited",
}
_ABSTRACT_HEADINGS = {"abstract", "executive summary", "summary"}


def _first_font_size(paragraph: Paragraph) -> float:
    """Largest explicit w:sz (in points) found in the paragraph, 0 when absent."""
    best = 0.0
    for sz in paragraph.element.iter(w("sz")):
        try:
            best = max(best, int(sz.get(w("val"))) / 2.0)
        except (TypeError, ValueError):
            continue
    return best


def _is_centered(paragraph: Paragraph) -> bool:
    ppr = paragraph.element.find(w("pPr"))
    if ppr is None:
        return False
    jc = ppr.find(w("jc"))
    return jc is not None and jc.get(w("val")) in {"center", "centre"}


def _is_blank(paragraph: Paragraph) -> bool:
    return not paragraph.text.strip()


def classify_regions(paragraphs: list[Paragraph]) -> None:
    """Assign front_matter / title / abstract / body / references / blank in place."""
    for p in paragraphs:
        p.region = "blank" if _is_blank(p) else "body"

    nonempty = [p for p in paragraphs if p.text.strip()]
    if not nonempty:
        return

    ref_head = None
    for p in nonempty:
        if p.normalized.lower().strip(" :") in _REF_HEADINGS:
            ref_head = p.index
            break
    abstract_head = None
    for p in nonempty:
        if p.normalized.lower().strip(" :") in _ABSTRACT_HEADINGS:
            abstract_head = p.index
            break

    # --- title -------------------------------------------------------------
    sizes = [s for s in (_first_font_size(p) for p in nonempty) if s > 0]
    body_size = sorted(sizes)[len(sizes) // 2] if sizes else 12.0

    title_idx = None
    best_score = 0
    for p in nonempty[:12]:
        key = p.normalized.lower().strip(" :")
        if key in _REF_HEADINGS or key in _ABSTRACT_HEADINGS:
            continue
        text = p.normalized
        words = text.split()
        if not (1 <= len(words) <= 16):
            continue
        score = 0
        style = p.style.lower()
        if "title" in style or style.startswith("heading"):
            score += 3
        if _is_centered(p):
            score += 2
        if _first_font_size(p) > body_size + 1:
            score += 2
        if text[:1].isupper() and not text.endswith("."):
            score += 1
        if len(words) == 1 and not (_is_centered(p) or p.is_heading):
            continue
        if score > best_score:
            best_score, title_idx = score, p.index

    if best_score < 2:
        title_idx = None

    # --- abstract block ----------------------------------------------------
    abstract_end = None
    if abstract_head is not None:
        following = [p for p in nonempty if p.index > abstract_head]
        prev_index = abstract_head
        for p in following:
            gap = p.index - prev_index - 1
            if gap >= 2 or (p.is_heading and gap >= 1):
                abstract_end = p.index
                break
            prev_index = p.index

    # --- body start --------------------------------------------------------
    if abstract_head is not None:
        after = [p for p in nonempty if p.index > abstract_head]
        if abstract_end is not None and abstract_end < 10 ** 9:
            after = [p for p in after if p.index >= abstract_end]
        pivot = next((p for p in after if len(p.words) >= 25), None)
        body_start = pivot.index if pivot is not None else (after[0].index if after else abstract_head + 1)
    else:
        floor = (title_idx + 1) if title_idx is not None else 0
        pivot = next((p for p in nonempty if p.index >= floor and len(p.words) >= 25), None)
        body_start = pivot.index if pivot is not None else (nonempty[-1].index + 1)

    # --- assign ------------------------------------------------------------
    for p in paragraphs:
        if _is_blank(p):
            p.region = "blank"
            continue
        if ref_head is not None and p.index >= ref_head:
            p.region = "references"
            continue
        if abstract_head is not None and p.index == abstract_head:
            p.region = "front_matter"
            continue
        if abstract_head is not None and abstract_head < p.index < min(body_start, abstract_end or 10 ** 9):
            p.region = "abstract"
            continue
        if p.index == title_idx:
            p.region = "title"
            continue
        if p.index < body_start:
            p.region = "front_matter"
            continue
        p.region = "body"


def detect_existing_comments(path: str) -> bool:
    import zipfile

    with zipfile.ZipFile(path) as z:
        return "word/comments.xml" in z.namelist()


def load_document(path: str, academic_style: str = "auto") -> DocumentModel:
    doc = Document(path)
    body = doc.element.body
    paragraphs: list[Paragraph] = []
    idx = 0
    for child in body.iterchildren():
        if child.tag == w("p"):
            paragraphs.append(build_paragraph(child, idx))
            idx += 1
        elif child.tag == w("tbl"):
            for p_el in child.iter(w("p")):
                paragraphs.append(build_paragraph(p_el, idx, in_table=True))
                idx += 1

    classify_regions(paragraphs)

    full = "\n\n".join(p.text for p in paragraphs if p.text.strip())
    fp = hashlib.sha1(re.sub(r"\s+", " ", full).strip().encode("utf-8")).hexdigest()

    style = academic_style
    if academic_style == "auto":
        style = detect_style(full, paragraphs)

    return DocumentModel(
        path=str(path),
        paragraphs=paragraphs,
        doc=doc,
        fingerprint=fp,
        style=style,
        has_existing_comments=detect_existing_comments(path),
        meta={"word_count": sum(len(p.words) for p in paragraphs)},
    )


def detect_style(text: str, paragraphs: list[Paragraph]) -> str:
    """Infer MLA vs APA from citations, headings and reference list shape."""
    apa_signals = 0
    mla_signals = 0
    low = text.lower()
    if re.search(r"\(\s*[A-Z][A-Za-z\-]+(?:\s+et al\.)?,\s*\d{4}", text):
        apa_signals += 3
    if re.search(r"\(\d{4}\)", text):
        apa_signals += 1
    if re.search(r"^abstract$", low, flags=re.MULTILINE):
        apa_signals += 2
    if "running head" in low:
        apa_signals += 2
    if re.search(r"\(\s*[A-Z][A-Za-z\-]+\s+\d{1,3}\)", text):
        mla_signals += 3
    if re.search(r"works cited", low):
        mla_signals += 3
    if re.search(r"^\s*[A-Z][a-z]+ [A-Z][a-z]+\s*$", text, flags=re.MULTILINE):
        mla_signals += 1
    for p in paragraphs:
        if p.region == "references":
            for line in p.text.split("\n"):
                if re.match(r"^[A-Z][A-Za-z\-\u2019']+,\s+[A-Z]\.", line):
                    apa_signals += 1
    return "apa" if apa_signals > mla_signals else "mla"


def strip_quotes(s: str) -> str:
    return s.strip().strip("\u201c\u201d\"'").strip()
