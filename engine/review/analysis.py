"""High-precision deterministic diagnostics for the ThinkingStorm review desk.

Every rule returns zero or more :class:`Finding` objects pointing at an exact
character span inside one paragraph.  Rules are written to *fire only on clear
evidence*: a missed comment is cheap, a wrong comment (anchored to the wrong
sentence, or diagnosing something the student did not do) is expensive.  The
human exemplars deliberately leave many paragraphs uncommented, and so do we.

Layout note: student drafts frequently break a paragraph in the middle of a
sentence (manual page breaks, copy/paste artefacts).  Rhetorical rules therefore
run over *logical blocks* -- consecutive paragraphs joined when the previous one
has no terminal punctuation or the next one starts in lower case -- while every
anchor is still mapped back to a single real paragraph, because Word comments
cannot span paragraphs.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Iterable

from .docmodel import DocumentModel, Paragraph, w, reference_heading_span
from .segmenter import Sentence, content_words, split_sentences

# Canonical ThinkingStorm knowledge-base categories.
THESIS = "THESIS STATEMENT"
INTRO = "INTRODUCTION"
ORGANISATION = "ORGANISATION"
TOPIC = "TOPIC SENTENCE"
TRANSITION = "TRANSITION"
EVIDENCE = "ANALYSIS OF EVIDENCE"
STATISTICS = "STATISTICS"
ANALYSIS = "ANALYSIS"
COUNTER = "COUNTER-ARGUMENT"
CONCLUSION = "CONCLUSION"
ABSTRACT = "ABSTRACT"
MLA = "MLA"
APA = "APA"
PUNCT = "PUNCTUATION"
FRAGMENTS = "FRAGMENTS"
SVA = "SUBJECT-VERB AGREEMENT"
INFORMAL = "INFORMAL WRITING"
CLARITY = "SENTENCE CLARITY"


@dataclass
class Finding:
    rule_id: str
    category: str
    paragraph: Paragraph
    start: int
    end: int
    facts: dict = field(default_factory=dict)
    priority: int = 50  # 0-100; higher wins when the comment budget is tight

    @property
    def quote(self) -> str:
        return self.paragraph.text[self.start:self.end]

    def key(self) -> tuple:
        return (self.rule_id, self.paragraph.index, self.start // 12)


# ---------------------------------------------------------------------------
# span helpers
# ---------------------------------------------------------------------------

_TRAILING = " \t\n\u00a0"


def trim_span(text: str, start: int, end: int) -> tuple[int, int]:
    """Trim whitespace and keep the span inside word boundaries."""
    start = max(0, min(start, len(text)))
    end = max(start, min(end, len(text)))
    # Word boundaries first: this can land on the whitespace before a word.
    while start > 0 and start < end and text[start - 1].isalnum() and text[start].isalnum():
        start += 1
    while end > start and end < len(text) and text[end - 1].isalnum() and text[end].isalnum():
        end -= 1
    while start < end and text[start] in _TRAILING:
        start += 1
    while end > start and text[end - 1] in _TRAILING:
        end -= 1
    return start, end


def sentence_span(sent: Sentence, max_chars: int = 190) -> tuple[int, int]:
    """A sentence span, shortened at a clause boundary when very long."""
    start, end = sent.start, sent.end
    if end - start <= max_chars:
        return start, end
    window = sent.text[:max_chars]
    cut = max(window.rfind("; "), window.rfind(", "), window.rfind(" and "))
    if cut >= 60:
        return start, start + cut + (1 if window[cut] == "," else 0)
    words = window.split()
    keep = " ".join(words[:-1])
    return start, start + len(keep)


def snippet_around(text: str, pos: int, width: int = 60) -> tuple[int, int]:
    start = max(0, pos - width // 2)
    end = min(len(text), pos + width // 2)
    return trim_span(text, start, end)


# ---------------------------------------------------------------------------
# logical blocks
# ---------------------------------------------------------------------------

@dataclass
class Block:
    paragraphs: list[Paragraph]
    text: str
    charmap: list[tuple[int, int]]  # block offset -> (paragraph position, local offset)

    def span_in_paragraph(self, start: int, end: int) -> tuple[Paragraph, int, int] | None:
        """Map a block span back to one concrete paragraph (clamped if it crosses)."""
        if not self.text or start >= end:
            return None
        start = max(0, min(start, len(self.text) - 1))
        end = max(start + 1, min(end, len(self.text)))
        p_start, local_start = self.charmap[start]
        p_end, local_end = self.charmap[end - 1]
        para_start = self.paragraphs[p_start]
        if p_start == p_end:
            s, e = trim_span(para_start.text, local_start, local_end + 1)
            return (para_start, s, e) if e - s >= 2 else None
        # Sentence straddles a paragraph break: anchor the part that holds most of it.
        tail = len(para_start.text) - local_start
        if tail >= 25:
            s, e = trim_span(para_start.text, local_start, len(para_start.text))
            return (para_start, s, e) if e - s >= 8 else None
        para_end = self.paragraphs[p_end]
        s, e = trim_span(para_end.text, 0, local_end + 1)
        return (para_end, s, e) if e - s >= 8 else None

    def sentences(self) -> list[Sentence]:
        return split_sentences(self.text)


def _is_continuation(prev: Paragraph, nxt: Paragraph) -> bool:
    prev_text = prev.text.rstrip()
    if not prev_text:
        return True
    stripped = nxt.text.lstrip()
    # A mid-sentence continuation is stronger evidence than paragraph length.
    # Some source files split a single sentence across several Word paragraphs.
    if stripped and stripped[0].islower():
        return True
    # Missing terminal punctuation does not erase a substantial paragraph's
    # boundary. Only join short extraction fragments, not whole student ideas.
    if len(prev.words) > 60:
        return False
    if prev_text[-1] not in ".!?\"\u201d\u2019)":
        return True
    return False


def build_blocks(model: DocumentModel) -> list[Block]:
    paras = [p for p in model.body_paragraphs if p.text.strip()]
    groups: list[list[Paragraph]] = []
    for p in paras:
        if groups and _is_continuation(groups[-1][-1], p):
            groups[-1].append(p)
        else:
            groups.append([p])

    blocks: list[Block] = []
    for group in groups:
        text_parts: list[str] = []
        charmap: list[tuple[int, int]] = []
        for i, p in enumerate(group):
            if i:
                text_parts.append(" ")
                charmap.append((i - 1, len(group[i - 1].text)))
            text_parts.append(p.text)
            charmap.extend((i, j) for j in range(len(p.text)))
        blocks.append(Block(group, "".join(text_parts), charmap))
    return blocks


# ---------------------------------------------------------------------------
# lexical helpers
# ---------------------------------------------------------------------------

_CITE_RE = re.compile(
    r"\(\s*(?P<authors>(?:[A-Z][A-Za-z'\u2019\-]+(?:\s+(?:et\s+al\.?|and|&)\s*)?)+)"
    r"(?:,)?\s*(?P<year>(?:19|20)\d{2})(?:,\s*p{1,2}\.\s*\d+)?\s*\)"
)
_NARRATIVE_CITE_RE = re.compile(
    r"\b(?P<authors>[A-Z][A-Za-z'\u2019\-]+(?:\s+(?:et\s+al\.?|and|&)\s+[A-Z][A-Za-z'\u2019\-]+)?)"
    r"\s*\((?P<year>(?:19|20)\d{2})\)"
)
_STAT_RE = re.compile(
    r"(?:\d+(?:\.\d+)?\s?%|\b\d[\d,\.]*\s+(?:million|billion|thousand)\b)"
)
_QUOTE_RE = re.compile(r'“[^“”]*”|"[^"\n]*"')


def quoted_passages(text: str):
    # Consume short titles too, then filter them out. Starting the regex only
    # at long quotations can pair a title's closing mark with the next opener.
    return (match for match in _QUOTE_RE.finditer(text) if len(match.group()[1:-1].split()) >= 8)

_TRANSITIONS = {
    "however", "although", "though", "while", "whereas", "nevertheless",
    "nonetheless", "furthermore", "moreover", "additionally", "similarly",
    "likewise", "consequently", "therefore", "thus", "meanwhile", "instead",
    "conversely", "despite", "because", "since", "after", "before", "first",
    "second", "third", "finally", "ultimately", "in contrast", "on the other hand",
    "for example", "for instance", "in addition", "as a result", "by contrast",
    "even though", "granted", "admittedly", "critics", "opponents",
}

_ANALYSIS_MARKERS = {
    "shows", "demonstrates", "suggests", "indicates", "reveals", "implies",
    "proves", "means", "signals", "illustrates", "underscores", "highlights",
    "confirms", "establishes", "this is important", "in other words",
    "matters", "consequently", "reflects", "exposes", "argues", "proves that",
    "which means", "so what", "the significance", "the implication",
}

_CLAIM_MARKERS = {
    "should", "must", "ought", "need to", "needs to", "argue", "argues",
    "arguing", "this essay", "this paper", "will explore", "will argue",
    "i believe", "i argue", "is necessary", "is essential", "is important",
    "the purpose", "aims to", "demonstrates that", "shows that", "proves that",
    "offer ways", "needed to", "required to", "is required", "are needed",
}

_GENERIC_HOOKS = [
    r"^throughout history",
    r"^since the beginning of time",
    r"^in today'?s society",
    r"^in today'?s world",
    r"^in recent years",
    r"^everyone (?:knows|has|goes|wants)",
    r"^all people",
    r"^many people (?:believe|think|say|wonder)",
    r"^it is (?:a )?(?:well[- ]known|common)",
    r"^from the dawn of",
    r"^in the modern (?:world|era)",
]

_INFORMAL = [
    "dramatically", "huge", "really", "very", "stuff", "things", "a lot",
    "lots of", "kind of", "sort of", "pretty much", "totally", "super",
    "insane", "crazy", "a bunch",
]

_WORDINESS = {
    "the reason for that is because": "the cause is",
    "due to the fact that": "because",
    "in order to": "to",
    "has the ability to": "can",
    "at this point in time": "now",
    "in the event that": "if",
    "a large number of": "many",
    "for the purpose of": "to",
    "is able to": "can",
}

_VAGUE_THESIS_WORDS = {
    "many", "various", "several", "numerous", "different", "important",
    "significant", "big", "huge", "major", "a lot", "things", "aspects",
    "factors", "issues", "ways", "strategies", "approaches", "solutions",
    "impacts", "affects", "changes",
}

_IMPLICATION_MARKERS = {
    "should", "must", "need", "important", "significant", "future", "implication",
    "implications", "policy", "society", "recommend", "solution", "ensure",
    "critical", "essential", "urgent", "action", "if we", "going forward",
    "the larger", "broader",
}

_PIVOT_STARTS = (
    "the problem also", "the issue also", "another", "in addition", "additionally",
    "beyond this", "more importantly", "at the same time",
)

_MODAL_CLAIM = re.compile(r"\b(should|must|ought|need|needs|required|necessary)\b", re.I)
_MODAL_SOFT = re.compile(r"\b(would|will|can|may|might|could)\b", re.I)
_EVALUATIVE = re.compile(
    r"\b(important|significant|essential|critical|positive|negative|effective|"
    r"beneficial|harmful|impact|consequence|solution|approach|strateg\w*|"
    r"necessary|valuable|dangerous|urgent)\b",
    re.I,
)


def _has_any(text_low: str, markers: Iterable[str]) -> bool:
    return any(m in text_low for m in markers)


def _citation_spans(text: str) -> list[re.Match]:
    found = list(_CITE_RE.finditer(text))
    seen = {(m.start(), m.end()) for m in found}
    for m in _NARRATIVE_CITE_RE.finditer(text):
        if (m.start(), m.end()) not in seen:
            found.append(m)
    return found


def _sources(text: str) -> list[str]:
    names = []
    for m in _citation_spans(text):
        name = re.sub(r"\s+", " ", m.group("authors").strip().rstrip(","))
        if name and name.lower() not in {n.lower() for n in names}:
            names.append(name)
    return names


def _jaccard(a: str, b: str) -> float:
    wa, wb = set(content_words(a)), set(content_words(b))
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def _finite_verb(sentence: str) -> bool:
    low = " " + sentence.lower() + " "
    verbs = re.findall(
        r"\b(is|are|was|were|be|been|am|has|have|had|do|does|did|can|could|will|"
        r"would|should|may|might|must|shall|[a-z]+(?:s|ed|ing))\b",
        low,
    )
    return any(not v.endswith("ing") for v in verbs)


def _evidence_in(sentence_text: str) -> bool:
    return bool(
        _citation_spans(sentence_text)
        or _STAT_RE.search(sentence_text)
        or next(quoted_passages(sentence_text), None)
    )


# ---------------------------------------------------------------------------
# front matter / formatting
# ---------------------------------------------------------------------------

_DATE_NUMERIC = re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b|\b\d{4}-\d{2}-\d{2}\b")
_MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|"
    "November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec"
)


def _find_line(paragraphs: list[Paragraph], pattern: re.Pattern) -> Paragraph | None:
    for p in paragraphs:
        if pattern.search(p.normalized):
            return p
    return None


def _header_has_page_number(model: DocumentModel) -> bool:
    try:
        for section in model.doc.sections:
            for hdr in (section.header, section.first_page_header, section.even_page_header):
                try:
                    xml = hdr._element.xml
                except Exception:
                    continue
                if "PAGE" in xml or "fldSimple" in xml:
                    return True
    except Exception:
        pass
    return False


def _is_title_case(text: str) -> bool:
    minor = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "at",
             "by", "in", "of", "on", "to", "up", "as", "per", "via", "vs"}
    words = re.findall(r"[A-Za-z][A-Za-z'\u2019\-]*", text)
    if not words:
        return True
    for i, word in enumerate(words):
        if i not in (0, len(words) - 1) and word.lower() in minor:
            continue
        if not word[0].isupper():
            return False
    return True


def _is_center_aligned(paragraph) -> bool:
    ppr = paragraph.element.find(w("pPr"))
    if ppr is None:
        return False
    jc = ppr.find(w("jc"))
    return jc is not None and jc.get(w("val")) in {"center", "both"}


_FORMULAIC_OPINION = re.compile(
    r"\b(?:in my (?:interpretation|view|perspective|opinion)|"
    r"my (?:portrayal|view|perspective) is|i believe)\b",
    re.I,
)

_COMMON_MISSPELLINGS = {
    "zues": "Zeus",
    "kan academy": "Khan Academy",
    "alot": "a lot",
    "recieve": "receive",
    "seperate": "separate",
    "definately": "definitely",
    "occured": "occurred",
    "goverment": "government",
    "enviroment": "environment",
    "accomodate": "accommodate",
    "untill": "until",
    "thier": "their",
    "commited": "committed",
    "begining": "beginning",
    "sucessful": "successful",
    "independant": "independent",
    "publically": "publicly",
    "recomend": "recommend",
}


def front_matter_rules(model: DocumentModel) -> list[Finding]:
    out: list[Finding] = []
    # The front of a clinical evaluation contains patient identifiers and
    # assessment dates, not an essay's student title-page block.
    if getattr(model, "_essay_type", "") == "report":
        return out
    fm = [p for p in model.front_matter if p.text.strip()]
    if not fm:
        return out

    date_p = _find_line(fm, re.compile(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"))
    if date_p is not None:
        m = _DATE_NUMERIC.search(date_p.text)
        if m:
            start, end = trim_span(date_p.text, m.start(), m.end())
            rule = "mla_date_numeric" if model.style == "mla" else "apa_date_numeric"
            out.append(Finding(rule, MLA if model.style == "mla" else APA,
                               date_p, start, end, {"date": m.group(0)}, 86))

    if model.style == "mla":
        idx_course = idx_instructor = idx_date = None
        for i, p in enumerate(fm):
            t = p.normalized
            if re.search(r"\b[A-Z]{2,4}\s?\d{2,4}[A-Z]?\b", t):
                idx_course = i
            if re.match(r"^(?:Mr|Mrs|Ms|Dr|Professor|Prof)\.?\s", t):
                idx_instructor = i
            if _DATE_NUMERIC.search(t) or re.match(rf"^\d{{1,2}}\s+(?:{_MONTHS})\b", t):
                idx_date = i
        disorder = False
        if idx_date is not None and idx_instructor is not None and idx_date < idx_instructor:
            disorder = True
        if idx_date is not None and idx_course is not None and idx_date < idx_course:
            disorder = True
        if disorder:
            anchor_para = fm[idx_instructor] if (
                idx_instructor is not None and idx_date < idx_instructor
            ) else (fm[idx_course] if idx_course is not None else fm[idx_date])
            s, e = trim_span(anchor_para.text, 0, len(anchor_para.text))
            out.append(Finding("mla_heading_order", MLA, anchor_para, s, e, {}, 80))

        # Two heading elements typed on one line (name + instructor).
        for p in fm:
            if re.search(r"\S\s+(?:Professor|Prof\.|Dr\.|Mr\.|Mrs\.|Ms\.)\s+\S", p.text):
                s, e = trim_span(p.text, 0, len(p.text))
                out.append(Finding("mla_heading_same_line", MLA, p, s, e, {}, 72))
                break

        if not _header_has_page_number(model):
            anchor = fm[0]
            s, e = trim_span(anchor.text, 0, len(anchor.text))
            out.append(Finding("mla_header_missing", MLA, anchor, s, e, {}, 74))

        # MLA headings are flush left; a centered name block reads as a title
        # page. Only flag when every heading line is centered.
        heading_lines = fm[:4]
        if len(heading_lines) >= 3 and all(_is_center_aligned(p) for p in heading_lines):
            anchor = heading_lines[1] if len(heading_lines) > 1 else heading_lines[0]
            s, e = trim_span(anchor.text, 0, len(anchor.text))
            out.append(Finding("mla_heading_alignment", MLA, anchor, s, e, {}, 62))
    else:
        has_instructor = any(
            re.match(r"^(?:Mr|Mrs|Ms|Dr|Professor|Prof)\.?\s", p.normalized) for p in fm
        )
        if not has_instructor:
            anchor = fm[0]
            s, e = trim_span(anchor.text, 0, len(anchor.text))
            out.append(Finding("apa_instructor_missing", APA, anchor, s, e, {}, 70))
        for p in fm:
            if re.fullmatch(r"[A-Za-z]{2,4}\s?-?\s?\d{2,4}[A-Z]?", p.normalized):
                s, e = trim_span(p.text, 0, len(p.text))
                out.append(Finding("apa_course_name", APA, p, s, e, {}, 58))

    title = next((p for p in model.paragraphs if p.region == "title"), None)
    if title is not None:
        t = title.normalized
        if model.style == "mla" and t and not _is_title_case(t):
            s, e = trim_span(title.text, 0, len(title.text))
            out.append(Finding("mla_title_case", MLA, title, s, e, {}, 66))
        if t.endswith("."):
            s, e = trim_span(title.text, 0, len(title.text))
            out.append(Finding("title_period", MLA, title, s, e, {}, 55))
    return out


# ---------------------------------------------------------------------------
# abstract
# ---------------------------------------------------------------------------

def abstract_rules(model: DocumentModel) -> list[Finding]:
    out: list[Finding] = []
    paras = [p for p in model.paragraphs if p.region == "abstract"]
    if not paras:
        return out
    text = " ".join(p.text for p in paras)
    low = text.lower()
    snapshot = ("the results", "findings", "this study found", "we found",
                "the findings", "results show", "this research found", "conclusion")
    roadmap = ("this paper discusses", "this essay", "will discuss", "will explore",
               "in this paper", "i will", "this review paper", "the following")
    if _has_any(low, roadmap) and not _has_any(low, snapshot):
        sentences = split_sentences(paras[0].text)
        if sentences:
            s, e = sentence_span(sentences[0])
            out.append(Finding("abstract_intro", ABSTRACT, paras[0], s, e, {}, 78))
    return out


# ---------------------------------------------------------------------------
# thesis / introduction
# ---------------------------------------------------------------------------

def _intro_blocks(blocks: list[Block]) -> list[Block]:
    if not blocks:
        return []
    intro = blocks[:1]
    if len(blocks) > 1 and len(blocks[0].text.split()) < 30:
        intro = blocks[:2]
    return intro


def _thesis_score(sentence: str) -> int:
    low = sentence.lower()
    words = sentence.split()
    score = 0
    if _MODAL_CLAIM.search(low):
        score += 3
    if _MODAL_SOFT.search(low):
        score += 1
    if _EVALUATIVE.search(low):
        score += 2
    if re.search(r"\b(this essay|this paper|argue|argues|demonstrat\w*|"
                 r"shows that|suggests that|aims to)\b", low):
        score += 3
    if 10 <= len(words) <= 45:
        score += 2
    if _citation_spans(sentence):
        score -= 2
    if re.search(r"\baccording to\b", low):
        score -= 3
    if sentence.strip().endswith("?"):
        score -= 4
    if len(words) < 7:
        score -= 3
    return score


def thesis_rules(model: DocumentModel, blocks: list[Block]) -> list[Finding]:
    out: list[Finding] = []
    intro = _intro_blocks(blocks)
    if not intro:
        return out

    entries: list[tuple[Block, Sentence, int]] = []
    for block in intro:
        for sent in block.sentences():
            if len(sent.words) >= 6:
                entries.append((block, sent, _thesis_score(sent.text)))
    if not entries:
        return out

    last_block, last_sent, _ = entries[-1]
    entries = [
        (b, s, sc + (3 if s is last_sent and sc >= 2 else 0)) for b, s, sc in entries
    ]
    entries.sort(key=lambda x: x[2], reverse=True)
    best_block, best_sent, best_score = entries[0]
    low = best_sent.text.lower()

    if getattr(model, "_essay_type", "") == "rhetorical" and not re.search(
        r"\b(ethos|pathos|logos|rhetorical appeal|appeals)\b", low
    ):
        mapped = best_block.span_in_paragraph(best_sent.start, best_sent.end)
        if mapped:
            out.append(Finding("thesis_rhetorical_missing", THESIS, *mapped, {}, 84))
        return out

    vague = [word for word in _VAGUE_THESIS_WORDS if re.search(rf"\b{re.escape(word)}\b", low)]
    too_long = len(best_sent.words) > 45
    previews = bool(re.search(
        r"\b(three|two|both|first|second|third|finally|as well as)\b|:",
        best_sent.text,
    )) or bool(re.search(r"\b(ethos|pathos|logos)\b", low))

    if best_score < 6 and not vague:
        mapped = last_block.span_in_paragraph(last_sent.start, last_sent.end)
        if mapped and len(last_sent.words) >= 8:
            out.append(Finding("thesis_missing", THESIS, *mapped, {}, 88))
        return out

    if vague:
        mapped = best_block.span_in_paragraph(best_sent.start, best_sent.end)
        if mapped:
            out.append(Finding(
                "thesis_vague", THESIS, *mapped,
                {"vague": vague[:3], "words": len(best_sent.words),
                 "thesis": best_sent.text.strip()}, 82,
            ))
    elif too_long:
        mapped = best_block.span_in_paragraph(best_sent.start, best_sent.end)
        if mapped:
            out.append(Finding('thesis_long', THESIS, *mapped, {'words': len(best_sent.words)}, 82))
    elif not previews and best_score <= 8:
        mapped = best_block.span_in_paragraph(best_sent.start, best_sent.end)
        if mapped:
            out.append(Finding("thesis_no_preview", THESIS, *mapped,
                               {"words": len(best_sent.words)}, 78))

    strong = [(b, s, sc) for b, s, sc in entries if sc >= 7 and len(s.words) <= 25]
    if len(strong) >= 2:
        ordered = sorted(strong[:2], key=lambda x: x[1].start)
        second_block, second_sent, _ = ordered[1]
        mapped = second_block.span_in_paragraph(second_sent.start, second_sent.end)
        if mapped and not out:
            out.append(Finding("thesis_spread", THESIS, *mapped, {}, 80))

    first_sent = blocks[0].sentences()
    if first_sent:
        low0 = first_sent[0].text.lower().strip()
        for pat in _GENERIC_HOOKS:
            if re.search(pat, low0):
                mapped = blocks[0].span_in_paragraph(first_sent[0].start, first_sent[0].end)
                if mapped:
                    out.append(Finding("intro_generic", INTRO, *mapped, {}, 72))
                break
    return out


# ---------------------------------------------------------------------------
# body rhetoric
# ---------------------------------------------------------------------------

def body_rules(model: DocumentModel, blocks: list[Block]) -> list[Finding]:
    out: list[Finding] = []
    genre = getattr(model, "_essay_type", "academic")
    essay_structure = genre not in {"bibliography", "report", "reflection"}
    sourced = sum(1 for b in blocks if _citation_spans(b.text) or _STAT_RE.search(b.text))
    essay_has_sources = sourced >= 2
    formulaic_total = sum(len(_FORMULAIC_OPINION.findall(p.text)) for p in model.body_paragraphs)

    for bi, block in enumerate(blocks):
        sentences = block.sentences()
        if not sentences:
            continue
        low = block.text.lower()

        # --- repeated opinion formula, short paragraph, known misspelling ---
        for para in block.paragraphs:
            text = para.text
            if formulaic_total >= 3:
                match = _FORMULAIC_OPINION.search(text)
                if match:
                    out.append(Finding(
                        "formulaic_opinion", CLARITY, para, match.start(), match.end(),
                        {"phrase": match.group(0).lower(), "count": formulaic_total}, 47,
                    ))
            words = len(para.words)
            if 5 <= words <= 25 and para.region == "body":
                s, e = trim_span(text, 0, len(text))
                out.append(Finding("paragraph_short", ORGANISATION, para, s, e,
                                   {"words": words}, 45))
            for wrong, right in _COMMON_MISSPELLINGS.items():
                pattern = (re.compile(rf"(?<!\w){re.escape(wrong)}(?!\w)", re.I)
                           if " " not in wrong else re.compile(re.escape(wrong), re.I))
                hit = pattern.search(text)
                if hit:
                    out.append(Finding("common_misspelling", CLARITY, para,
                                       hit.start(), hit.end(),
                                       {"wrong": hit.group(0), "right": right}, 58))
                    break

        # --- evidence without analysis ------------------------------------
        for j, sinfo in enumerate(sentences):
            if not _evidence_in(sinfo.text):
                continue
            following = sentences[j + 1: j + 3]
            if not following:
                # Evidence closes the paragraph with nothing said about it.
                if j == len(sentences) - 1 and len(sentences) >= 2:
                    mapped = block.span_in_paragraph(sinfo.start, sinfo.end)
                    if mapped:
                        stats = _STAT_RE.findall(sinfo.text)
                        cat = STATISTICS if stats else EVIDENCE
                        out.append(Finding("evidence_no_analysis", cat, *mapped,
                                           {"stat": stats[0] if stats else "",
                                            "source": _sources(sinfo.text)[:1]}, 70))
                break
            nxt = following[0]
            nxt_low = nxt.text.lower().strip()
            pivot = any(nxt_low.startswith(p) for p in _PIVOT_STARTS)
            has_analysis = _has_any(" ".join(s.text for s in following).lower(), _ANALYSIS_MARKERS)
            if has_analysis:
                continue
            if pivot:
                mapped = block.span_in_paragraph(sinfo.start, sinfo.end)
                if mapped:
                    stats = _STAT_RE.findall(sinfo.text)
                    cat = STATISTICS if stats and not _citation_spans(sinfo.text) else EVIDENCE
                    out.append(Finding(
                        "evidence_no_analysis", cat, *mapped,
                        {"stat": stats[0] if stats else "",
                         "source": _sources(sinfo.text)[:1]}, 70,
                    ))
                    break

        # --- quotation from a source known to have numbered pages ----------
        if model.style == "mla":
            paginated = []
            for reference in model.references:
                if re.search(r'\bpp?\.\s*\d+|\)\s*[,.:]\s*\d+\s*[-–]\s*\d+', reference.text):
                    key = reference.normalized.split(',', 1)[0].split('.', 1)[0].strip()
                    if len(key) >= 2 and re.search(r'(?<!\w)' + re.escape(key) + r'(?!\w)', block.text, re.I):
                        paginated.append(key)
            # A web address or quotation alone does not establish pagination.
            # MLA does not require an invented number for an unpaginated source.
            for j, sinfo in enumerate(sentences):
                if not paginated:
                    break
                for qm in quoted_passages(sinfo.text):
                    attribution = sinfo.text[:qm.start()] + ' ' + sinfo.text[qm.end():]
                    local_sources = [key for key in paginated if re.search(
                        r'(?<!\w)' + re.escape(key) + r'(?!\w)', attribution, re.I)]
                    if len(local_sources) != 1:
                        continue
                    window = sinfo.text
                    if j + 1 < len(sentences):
                        window += " " + sentences[j + 1].text
                    if re.search(r"\([^)]*\d+[^)]*\)", window):
                        break
                    if re.search(r"\b[A-Z][a-z]+\s+\d{1,3}\b", window):
                        break
                    start = sinfo.start + qm.start()
                    end = sinfo.start + qm.end()
                    mapped = block.span_in_paragraph(start, end)
                    if mapped:
                        out.append(Finding("quote_no_page", MLA, *mapped, {'source': local_sources[0]}, 60))
                    break
                else:
                    continue
                break

        # --- topic sentence opens with evidence ---------------------------
        first = sentences[0]
        first_low = first.text.lower().strip()
        if essay_structure and (first_low.startswith("according to") or _citation_spans(first.text)
                or _STAT_RE.search(first.text)) and len(sentences) >= 2:
            mapped = block.span_in_paragraph(first.start, first.end)
            if mapped:
                out.append(Finding("topic_evidence_opener", TOPIC, *mapped, {}, 58))

        # --- overlong paragraph -------------------------------------------
        if len(block.text.split()) > 150 and len(sentences) >= 6:
            # Anchor the sentence that actually makes the paragraph long. The
            # midpoint can land on a short demonstrative sentence that other
            # rules also quote, which blocks a second comment on the paragraph.
            middle = max(sentences, key=lambda s: len(s.words))
            mapped = block.span_in_paragraph(*sentence_span(middle))
            if mapped:
                out.append(Finding("paragraph_overlong", ORGANISATION, *mapped,
                                   {"words": len(block.text.split())}, 52))

        # --- a list of studies without synthesis --------------------------
        sources = _sources(block.text)
        if genre != "bibliography" and len(sources) >= 2 and not _has_any(
            low, ("similarly", "by contrast", "both", "together", "whereas",
                  "in comparison", "compared", "combined")
        ):
            anchor_sent = next((s for s in sentences if _citation_spans(s.text)), sentences[0])
            mapped = block.span_in_paragraph(anchor_sent.start, anchor_sent.end)
            if mapped:
                out.append(Finding("study_listing", EVIDENCE, *mapped,
                                   {"sources": sources[:3]}, 62))

        # --- abrupt topic shift between blocks ----------------------------
        if essay_structure and 0 < bi < len(blocks) - 1:
            prev_sents = blocks[bi - 1].sentences()
            first = sentences[0]
            first_low = first.text.lower().strip()
            starts_with_transition = any(
                first_low.startswith(t + " ") or first_low.startswith(t + ",")
                for t in _TRANSITIONS
            )
            prev_ends = blocks[bi - 1].text.rstrip()[-1:] in ".!?\"\u201d"
            if prev_sents and prev_ends and not starts_with_transition \
                    and first.text[:1].isupper() and len(first.words) >= 9:
                prev_words = set(content_words(blocks[bi - 1].text))
                first_words = set(content_words(first.text))
                carried = len(first_words & prev_words) / max(1, len(first_words))
                # A proper noun already introduced earlier keeps the thread alive.
                earlier_text = " ".join(b.text for b in blocks[:bi])
                names = set(re.findall(r"\b[A-Z][a-z]{2,}\b", first.text))
                known = {n for n in names if re.search(rf"\b{re.escape(n)}\b", earlier_text)}
                if (_jaccard(first.text, prev_sents[-1].text) < 0.04
                        and carried < 0.10 and not known):
                    mapped = block.span_in_paragraph(first.start, first.end)
                    if mapped:
                        out.append(Finding("transition_abrupt", TRANSITION, *mapped, {}, 56))

        # --- repeated paragraph opener -------------------------------------
        if bi > 0:
            prev_first = blocks[bi - 1].sentences()
            if prev_first:
                a = re.findall(r"[a-z']+", prev_first[0].text.lower())[:2]
                b = re.findall(r"[a-z']+", first.text.lower())[:2]
                if len(a) == 2 and a == b and len(first.words) >= 8:
                    mapped = block.span_in_paragraph(first.start, first.end)
                    if mapped:
                        out.append(Finding("repeated_opener", ORGANISATION, *mapped,
                                           {"opener": " ".join(a)}, 54))

        # --- informal diction ---------------------------------------------
        for term in _INFORMAL:
            m = re.search(rf"\b{re.escape(term)}\b", low)
            if m:
                mapped = block.span_in_paragraph(m.start(), m.end())
                if mapped:
                    out.append(Finding("informal_diction", INFORMAL, *mapped,
                                       {"term": term}, 60))
                break

        # --- wordiness ------------------------------------------------------
        for phrase in _WORDINESS:
            m = re.search(rf"\b{re.escape(phrase)}\b", low)
            if m:
                mapped = block.span_in_paragraph(m.start(), m.end())
                if mapped:
                    para, s, e = mapped
                    s2, e2 = snippet_around(para.text, s, 90)
                    out.append(Finding("wordiness", CLARITY, para, s2, e2,
                                       {"phrase": phrase}, 58))
                break

        # --- demonstrative "This" with no noun ------------------------------
        for sinfo in sentences:
            m = re.match(r"^(?:this|these)\s+(?:shows|proves|means|suggests|"
                         r"demonstrates|creates|leads|helps|makes)\b", sinfo.text.strip(), re.I)
            if m and len(sinfo.words) > 6:
                # Anchor the demonstrative phrase, not the whole sentence: a
                # sentence-wide span collides with sentence-level rules and
                # prevents a second, distinct comment on the same paragraph.
                mapped = block.span_in_paragraph(sinfo.start + m.start(),
                                                 sinfo.start + m.end())
                if mapped:
                    out.append(Finding("vague_pronoun", CLARITY, *mapped, {}, 52))
                break

        # --- comma splice ----------------------------------------------------
        for sinfo in sentences:
            m = re.search(r",\s+(however|therefore|thus|consequently|moreover|furthermore)\s+([a-z]+)", sinfo.text, re.I)
            if not m:
                continue
            follower = m.group(2).lower()
            if follower.endswith("ing"):
                continue
            if re.match(r"^(?:it|they|we|you|he|she|this|these|the|there|i)\b", follower):
                mapped = block.span_in_paragraph(sinfo.start, sinfo.end)
                if mapped:
                    out.append(Finding("comma_splice", PUNCT, *mapped, {}, 54))
                break

        # --- paragraph coverage: claim without support ---------------------
        words = len(block.text.split())

        # --- paragraph coverage: filler repetition -------------------------
        if words >= 45:
            filler = {"very": 0, "really": 0, "also": 0, "many": 0, "things": 0,
                      "important": 0, "different": 0, "various": 0, "a lot": 0}
            for term in filler:
                filler[term] = len(re.findall(rf"\b{re.escape(term)}\b", low))
            term, count = max(filler.items(), key=lambda kv: kv[1])
            if count >= 4:
                m = re.search(rf"\b{re.escape(term)}\b", low)
                mapped = block.span_in_paragraph(m.start(), m.end()) if m else None
                if mapped:
                    out.append(Finding("para_filler", CLARITY, *mapped,
                                       {"term": term, "count": count}, 46))

        # --- paragraph coverage: metronomic sentences ----------------------
        if len(sentences) >= 4:
            lengths = [len(s.words) for s in sentences]
            mean_len = sum(lengths) / len(lengths)
            var = sum((x - mean_len) ** 2 for x in lengths) / len(lengths)
            if var ** 0.5 < 2.4 and 10 <= mean_len <= 26:
                mapped = block.span_in_paragraph(sentences[0].start, sentences[0].end)
                if mapped:
                    out.append(Finding("para_monotone", CLARITY, *mapped,
                                       {"mean": round(mean_len)}, 45))

        # --- paragraph coverage: passive constructions ---------------------
        if words >= 55:
            passives = list(re.finditer(
                r"\b(?:is|are|was|were|be|been|being)\s+[a-z]+(?:ed|en)\b", block.text, re.I))
            if len(passives) >= 2:
                mapped = block.span_in_paragraph(passives[0].start(), passives[0].end())
                if mapped:
                    para, s, e = mapped
                    s2, e2 = snippet_around(para.text, s, 80)
                    out.append(Finding("para_passive", CLARITY, para, s2, e2,
                                       {"count": len(passives)}, 47))

        # --- paragraph coverage: opens without a claim ---------------------
        if essay_structure and len(sentences) >= 4 and 0 < bi < len(blocks) - 1:
            first_low = sentences[0].text.lower().strip()
            starts_with_transition = any(
                first_low.startswith(t + " ") or first_low.startswith(t + ",")
                for t in _TRANSITIONS
            )
            fact_opening = re.match(r'^(?:there (?:is|are) \d|(?:in|during) (?:the )?\d{4}\b|.{1,50}\b(?:was born|was published|is located)\b)', first_low)
            if fact_opening and not starts_with_transition and not _MODAL_CLAIM.search(first_low) \
                    and not _has_any(first_low, _CLAIM_MARKERS):
                mapped = block.span_in_paragraph(sentences[0].start, sentences[0].end)
                if mapped:
                    out.append(Finding("para_no_claim", TOPIC, *mapped, {}, 49))

        if (essay_structure and essay_has_sources and bi < len(blocks) - 1 and words >= 55
                and not _citation_spans(block.text) and not _STAT_RE.search(block.text)):
            mapped = block.span_in_paragraph(sentences[0].start, sentences[0].end)
            if mapped:
                out.append(Finding("para_unsupported", EVIDENCE, *mapped, {}, 50))

        # Low vocabulary overlap between an opening and ending does not by
        # itself establish paragraph drift. That requires a semantic review.

    return out


def conclusion_rules(model: DocumentModel, blocks: list[Block]) -> list[Finding]:
    out: list[Finding] = []
    if len(blocks) < 3:
        return out
    conclusion = blocks[-1]
    c_words = set(content_words(conclusion.text))
    if not c_words:
        return out
    earlier: set[str] = set()
    for block in blocks[:-1]:
        earlier |= set(content_words(block.text))
    containment = len(c_words & earlier) / max(1, len(c_words))
    low = conclusion.text.lower()
    sentences = conclusion.sentences()

    forward_looking = any(
        marker in low for marker in
        ("implication", "broader", "larger picture", "society as a whole", "policy",
         "recommend", "going forward", "long term", "long-term", "next steps",
         "what this means", "future research", "future generations")
    )
    short = len(conclusion.text.split()) < 70
    if not sentences or forward_looking:
        return out
    if containment >= 0.40 or (containment >= 0.28 and short):
        mapped = conclusion.span_in_paragraph(sentences[-1].start, sentences[-1].end)
        if mapped:
            out.append(Finding("conclusion_summary", CONCLUSION, *mapped,
                               {"overlap": round(containment, 2)}, 76))

    # A one-sentence closing paragraph in a multi-paragraph essay is usually a
    # list of points rather than a synthesis.
    last_para = model.body_paragraphs[-1] if model.body_paragraphs else None
    if last_para is not None and len(last_para.words) < 60 and len(model.prose_paragraphs) >= 3:
        para_sents = split_sentences(last_para.text)
        if para_sents and not forward_looking:
            s, e = sentence_span(para_sents[0])
            out.append(Finding("conclusion_thin", CONCLUSION, last_para, s, e,
                               {"words": len(last_para.words)}, 64))
    return out


def counterargument_rules(model: DocumentModel, blocks: list[Block]) -> list[Finding]:
    out: list[Finding] = []
    if len(blocks) < 4:
        return out
    text = " ".join(b.text for b in blocks).lower()
    if not re.search(r"\b(should|must|ought|need to)\b", text):
        return out
    if re.search(r"\b(however|although|though|critics|opponents|skeptics|"
                 r"on the other hand|while it is true|some argue|detractors)\b", text):
        return out
    block = blocks[len(blocks) // 2]
    sentences = block.sentences()
    if not sentences:
        return out
    mapped = block.span_in_paragraph(sentences[0].start, sentences[0].end)
    if mapped:
        out.append(Finding("counterargument_missing", COUNTER, *mapped, {}, 48))
    return out


# ---------------------------------------------------------------------------
# mechanics
# ---------------------------------------------------------------------------

_SVA_PATTERNS = [
    (re.compile(r"\b(?:nor|neither)\s+(?:does|do|is|are|has|have|was|were)\s+(they|we|you)\b", re.I), "aux"),
    (re.compile(r"\b(?:one|each|every|neither|either)\s+of\s+[^.,;]{2,40}?\s+(are|were|have)\b", re.I), "quant"),
    (re.compile(r"\bthere\s+(?:is|was)\s+(?:many|several|multiple|numerous|two|three|four|five)\b", re.I), "there"),
    (re.compile(r"\b(?:the|this|that)\s+(?:programs|students|policies|studies|researchers|results|effects|approaches)\s+(?:helps|has|is|was|does)\b", re.I), "plural"),
    (re.compile(r"(?<!\bif )(?<!\bas )\b(?:he|she|it)\s+(?:have|were|are)\b", re.I), "sing"),
    (re.compile(r"\b(?:programs|policies|results|studies|approaches|systems|methods|benefits)\b[^.!?]{0,70}?\bit\b", re.I), "pronoun"),
    (re.compile(r"(?:(?<=^)|(?<=[.!?]))\s*(?:[A-Z][\w'\u2019-]*\s+)?[\w'\u2019-]+\s+and\s+[\w'\u2019-]+\s+(?:helps|has|is|was|does|shows|makes)\b"), "compound"),
]

_SPACING_PATTERNS = [    (re.compile(r"(?<=\S)[ \t]+[.,;:](?![\d.])"), "space_before_punct"),
    (re.compile(r"\b\w+\.\s*\."), "double_period"),
    (re.compile(r"[,;:][A-Za-z]"), "missing_space_after_punct"),
    (re.compile(r"(?<=[a-z])[.!?](?=[A-Z])"), "missing_space_after_punct"),
    (re.compile(r"\)\s+\."), "citation_period_space"),
    (re.compile(r"(?<=\S) {2,}(?=\S)"), "double_space"),
]


_PARTICIPLE_OPENERS = ("using", "having", "including", "given", "based on",
                       "despite", "starting", "according to")
_CURRENT_YEAR = datetime.now(timezone.utc).year
_AUX_RE = re.compile(
    r"\b(?:is|are|was|were|be|been|am|has|have|had|do|does|did|can|could|will|"
    r"would|should|may|might|must)\b", re.I)

# Compact verb lexicon for clause detection (no POS tagger dependency).
_VERBS = {
    "show", "suggest", "argue", "demonstrate", "explain", "describe", "use", "create",
    "provide", "cause", "lead", "increase", "reduce", "help", "make", "give", "take",
    "become", "remain", "seem", "appear", "allow", "require", "need", "include",
    "involve", "affect", "improve", "support", "prove", "reveal", "indicate",
    "illustrate", "highlight", "emphasize", "examine", "analyze", "compare",
    "consider", "discuss", "explore", "focus", "present", "state", "claim", "assert",
    "note", "find", "report", "observe", "study", "research", "test", "measure",
    "evaluate", "assess", "determine", "identify", "address", "solve", "prevent",
    "develop", "produce", "result", "contribute", "depend", "differ", "relate",
    "connect", "represent", "reflect", "serve", "play", "work", "happen", "occur",
    "exist", "continue", "change", "grow", "rise", "fall", "decline", "extend",
    "expand", "limit", "restrict", "protect", "harm", "benefit", "influence",
    "shape", "define", "matter", "mean", "propose", "recommend", "ensure", "avoid",
    "prefer", "choose", "apply", "offer", "gain", "earn", "save", "cost", "pay",
    "face", "experience", "believe", "think", "know", "want", "need", "expect",
    "agree", "disagree", "oppose", "challenge", "question", "answer", "conclude",
}
_IRREGULAR = {"grew", "grown", "went", "come", "came", "made", "took", "given",
              "gave", "found", "became", "began", "begun", "brought", "built",
              "wrote", "written", "said", "shown", "led", "ran", "saw", "seen",
              "thought", "told", "kept", "held", "left", "met", "paid", "put",
              "read", "rose", "sent", "set", "sat", "spoke", "spent", "stood",
              "taught", "understood", "won", "knew", "known", "felt", "meant"}


def _stem(token: str) -> str:
    if token.endswith("ies"):
        return token[:-3] + "y"
    if token.endswith("es") and token[:-2] in _VERBS:
        return token[:-2]
    if token.endswith("s") and token[:-1] in _VERBS:
        return token[:-1]
    if token.endswith("ed") and token[:-2] in _VERBS:
        return token[:-2]
    if token.endswith("ed") and token[:-1] in _VERBS:
        return token[:-1]
    return token


def _has_finite_verb(text: str) -> bool:
    if _AUX_RE.search(text):
        return True
    tokens = re.findall(r"[A-Za-z']+", text.lower())
    for i, token in enumerate(tokens):
        if token.endswith("ing"):
            continue
        if token in _IRREGULAR or token in _VERBS or _stem(token) in _VERBS:
            # Infinitives ("to give") do not make a clause finite.
            if i > 0 and tokens[i - 1] == "to":
                continue
            return True
    return False


def mechanics_rules(model: DocumentModel) -> list[Finding]:
    out: list[Finding] = []
    typo_examples: list[tuple[Paragraph, int, int, str]] = []

    for p in model.paragraphs:
        if p.region not in {"body", "abstract", "front_matter", "references"}:
            continue
        text = p.text
        protected_spacing = [m.span() for m in re.finditer(
            r'https?://\S+|\b(?:Ph|Ed|B|M)\.(?:D|Ed|A|S|Phil|Sc)\.?', text)]

        for pat, kind in _SVA_PATTERNS:
            m = pat.search(text)
            if m:
                sent = next((s for s in split_sentences(text)
                             if s.start < m.end() and m.start() < s.end), None)
                if sent is not None:
                    s, e = sentence_span(sent)
                else:
                    s, e = snippet_around(text, m.start(), 90)
                out.append(Finding("subject_verb", SVA, p, s, e, {"kind": kind}, 64))
                break

        for pat, rule in _SPACING_PATTERNS:
            for m in pat.finditer(text):
                if any(start <= m.start() and m.end() <= end for start, end in protected_spacing):
                    continue
                s, e = snippet_around(text, m.start(), 60)
                if e - s < 6:
                    continue
                # A short, human-readable specimen that includes the anomaly.
                frag_start = max(0, m.start() - 14)
                frag_end = min(len(text), m.end() + 10)
                while frag_start > 0 and text[frag_start - 1].isalnum():
                    frag_start -= 1
                while frag_end < len(text) and text[frag_end].isalnum():
                    frag_end += 1
                fragment = text[frag_start:frag_end].strip(" \t\n")
                if len(fragment) > 44:
                    cut = fragment.rfind(" ", 0, 44)
                    fragment = fragment[: cut if cut > 16 else 44].strip()
                typo_examples.append((p, s, e, rule, fragment))
                break

        for sinfo in split_sentences(text):
            s_low = sinfo.text.lower().strip()
            for opener in _PARTICIPLE_OPENERS:
                if not s_low.startswith(opener + " ") and not s_low.startswith(opener + ","):
                    continue
                if not _has_finite_verb(sinfo.text) and len(sinfo.words) >= 6:
                    s, e = sentence_span(sinfo)
                    out.append(Finding("fragment", FRAGMENTS, p, s, e, {}, 57))
                break

    if len(typo_examples) >= 2:
        p, s, e, _rule, _frag = typo_examples[0]
        examples = []
        for _para, _a, _b, rule, fragment in typo_examples:
            if rule == "double_space":
                continue  # an invisible anomaly reads poorly as a quoted example
            if fragment and fragment not in examples:
                examples.append(fragment)
        out.append(Finding("typo_cluster", PUNCT, p, s, e,
                           {"examples": examples[:5], "count": len(typo_examples)}, 68))
        for para, start, end, rule, fragment in typo_examples:
            if rule in {"space_before_punct", "citation_period_space", "double_period", "missing_space_after_punct"}:
                out.append(Finding(rule, PUNCT, para, start, end,
                                   {"specimen": fragment}, 65))
    elif len(typo_examples) == 1:
        p, s, e, rule, _frag = typo_examples[0]
        # A lone double space is noise; a space before punctuation is a real edit.
        if rule in {"space_before_punct", "citation_period_space", "double_period"}:
            out.append(Finding(rule, PUNCT, p, s, e, {}, 61))
    return out


# ---------------------------------------------------------------------------
# references
# ---------------------------------------------------------------------------

def _mla_container(text: str) -> tuple[int, int] | None:
    m = re.search(r"[\u201d\"]\.?\s*([A-Z][^,]{2,70}?),\s*(?:\d{4}|n\.d\.|vol\.)", text)
    if not m:
        return None
    return trim_span(text, m.start(1), m.end(1))


def _range_is_italic(paragraph: Paragraph, start: int, end: int) -> bool:
    covered = 0
    italic = 0
    for node in paragraph.nodes:
        if node.end <= start or node.start >= end:
            continue
        seg = max(0, min(end, node.end) - max(start, node.start))
        covered += seg
        if node.run is not None:
            rpr = node.run.find(w("rPr"))
            if rpr is None:
                continue
            flag = rpr.find(w('i'))
            if flag is None:
                flag = rpr.find(w('iCs'))
            if flag is not None and flag.get(w('val'), '1').lower() not in {'0', 'false', 'off'}:
                italic += seg
                continue
            if flag is not None:
                continue
            style = rpr.find(w("rStyle"))
            if style is not None and (style.get(w("val")) or "").lower() in {
                "emphasis", "intenseemphasis", "italic", "italics"
            }:
                italic += seg
    return covered > 0 and italic / covered > 0.6


def reference_rules(model: DocumentModel) -> list[Finding]:
    out: list[Finding] = []
    refs = [p for p in model.references if p.text.strip()]
    heading = next((p for p in refs if reference_heading_span(p.text)), None)

    if heading is not None and model.style == "mla":
        ppr = heading.element.find(w("pPr"))
        before = 0
        if ppr is not None:
            spacing = ppr.find(w("spacing"))
            if spacing is not None:
                try:
                    before = int(spacing.get(w("before")) or 0)
                except (TypeError, ValueError):
                    before = 0
        if before > 60:
            s, e = trim_span(heading.text, 0, len(heading.text))
            out.append(Finding("works_cited_top_margin", MLA, heading, s, e,
                               {"before": before}, 72))

    entries = [p for p in refs if p is not heading and len(p.words) >= 6
               and not re.match(r'^\s*https?://', p.text)]
    for p in entries:
        text = p.text
        stripped = text.rstrip()
        if stripped and stripped[-1] not in ".!?":
            start = stripped.rfind(" ", 0, len(stripped)) + 1
            s, e = trim_span(text, start, len(stripped))
            out.append(Finding("reference_missing_period",
                               MLA if model.style == "mla" else APA, p, s, e, {}, 56))
        if model.style == "mla":
            # A normal https://www... location is not a container-title error.
            m = re.search(r"(?<![/\w])Www\.[^\s,]+", text, re.I)
            if m:
                s, e = trim_span(text, m.start(), m.end())
                out.append(Finding("mla_raw_url_container", MLA, p, s, e, {}, 68))
            container = _mla_container(text)
            if container and not _range_is_italic(p, *container):
                s, e = container
                out.append(Finding("mla_container_italics", MLA, p, s, e, {}, 66))
        else:
            m = re.search(r"\b(PubMed|Google Scholar|JSTOR|ProQuest)\b", text)
            if m:
                s, e = trim_span(text, m.start(), m.end())
                out.append(Finding("apa_database", APA, p, s, e, {"db": m.group(1)}, 64))

        year_pattern = (r"[,.(]\s?(\d{4})," if model.style == "mla" else r"\((\d{4})[,)]")
        for year_match in re.finditer(year_pattern, text):
            year = int(year_match.group(1))
            if year < 1900 or (p.region == "references" and year > _CURRENT_YEAR + 1):
                s, e = trim_span(text, year_match.start(1), year_match.end(1))
                out.append(Finding("implausible_year", MLA if model.style == "mla" else APA,
                                   p, s, e, {}, 60))
                break

    if model.style == "apa":
        body_text = " ".join(p.text for p in model.body_paragraphs)
        refs_text = " ".join(p.text for p in entries)
        for short, long in (("WHO", "World Health Organization"),
                            ("CDC", "Centers for Disease Control and Prevention")):
            if long in body_text and re.match(rf"^{short}\b", refs_text):
                p = next((q for q in entries if re.match(rf"^{short}\b", q.text.strip())), None)
                if p is not None:
                    s, e = trim_span(p.text, 0, min(60, len(p.text)))
                    out.append(Finding("org_name_mismatch", APA, p, s, e,
                                       {"short": short, "long": long}, 62))
                    break
    return out


# ---------------------------------------------------------------------------
# aggregation
# ---------------------------------------------------------------------------

@dataclass
class AnalysisResult:
    findings: list[Finding]
    essay_type: str
    sources: list[str]
    metrics: dict
    blocks: list[Block]


_STATEMENT_OPENERS = [
    r"^i have always been (?:deeply )?passionate",
    r"^ever since i was a (?:child|kid)",
    r"^from (?:a|the) young age",
    r"^since i was young",
    r"^i have always (?:loved|wanted|dreamed|dreamt)",
    r"^as a (?:child|kid),? i",
]

_STATEMENT_CLICHES = {
    "world-class": "name the specific lab, centre, or course you want to work with",
    "world class": "name the specific lab, centre, or course you want to work with",
    "state-of-the-art": "replace this with the concrete facility or resource",
    "diverse student body": "say what the specific community would give you",
    "renowned faculty": "name the professor or research group you want to join",
    "top-tier": "name the programme feature that matters to you",
    "make a difference": "say what you would actually do, and for whom",
    "change the world": "name the concrete problem you want to work on",
    "leading software engineer": "name the kind of work you want to be doing",
}


def statement_rules(model: DocumentModel, blocks: list[Block]) -> list[Finding]:
    """Personal statement / admissions diagnostics."""
    out: list[Finding] = []
    if not blocks:
        return out

    first_block = blocks[0]
    sentences = first_block.sentences()
    if sentences:
        low = sentences[0].text.lower().strip()
        for pat in _STATEMENT_OPENERS:
            if re.search(pat, low):
                mapped = first_block.span_in_paragraph(sentences[0].start, sentences[0].end)
                if mapped:
                    out.append(Finding("statement_cliche_opener", INTRO, *mapped, {}, 84))
                break

    for bi, block in enumerate(blocks):
        low = block.text.lower()
        for phrase, hint in _STATEMENT_CLICHES.items():
            if phrase in low:
                m = re.search(rf"\b{re.escape(phrase)}\b", low)
                if m is None:
                    continue
                mapped = block.span_in_paragraph(m.start(), m.end())
                if mapped:
                    para, s, e = mapped
                    s2, e2 = snippet_around(para.text, s, 70)
                    out.append(Finding("statement_generic_claim", CLARITY, para, s2, e2,
                                       {"phrase": phrase, "hint": hint}, 72))
                break

    for block in blocks:
        low = block.text.lower()
        m = re.search(r"\b(?:in conclusion|to sum up|in summary)\b[,: ]", low)
        if m:
            mapped = block.span_in_paragraph(m.start(), m.end())
            if mapped:
                out.append(Finding("conclusion_announced", CONCLUSION, *mapped, {}, 66))
            break

    # A statement that never names a concrete place, person, or project is the
    # most common failure mode in admissions drafts.
    full = " ".join(b.text for b in blocks)
    if not re.search(r"\b(?:professor|prof\.|lab|laboratory|course|seminar|"
                     r"clinic|programme|program at|research group|centre|center)\b", full.lower()):
        target = next(
            (b for b in blocks
             if re.search(r"\b(?:program|programme|university|college|school|faculty)\b",
                          b.text.lower())),
            blocks[1] if len(blocks) > 1 else blocks[0],
        )
        sents = target.sentences()
        if sents:
            mapped = target.span_in_paragraph(sents[0].start, sents[0].end)
            if mapped:
                out.append(Finding("statement_no_specific_fit", ORGANISATION, *mapped, {}, 76))

    return out


def _essay_type(model: DocumentModel) -> str:
    opening = model.full_text[:1200].lower()
    if "annotated bibliography" in opening:
        return "bibliography"
    if re.search(r"\boccupational therapy evaluation\b|\bevaluation report\b", opening):
        return "report"
    raw_text = " ".join(p.text for p in model.body_paragraphs)
    text = raw_text.lower()
    if re.search(r"\bweek (?:one|1)\b", text) and re.search(r"\bweek (?:two|2)\b", text):
        return "reflection"
    if sum(text.count(k) for k in ("ethos", "pathos", "logos")) >= 2:
        return "rhetorical"
    if model.style == "apa" or len(_sources(raw_text)) >= 3:
        return "research"
    first_person = len(re.findall(r"\b(?:i|my|me|i'm|i've)\b", text))
    admissions = len(re.findall(
        r"\b(?:admission|program|programme|university|graduate|master'?s|ph\.?d|"
        r"school of|applicant|candidate)\b", text))
    if first_person >= 5 and admissions >= 2 and len(_sources(raw_text)) < 2:
        return "statement"
    if re.search(r"\b(should|must|ought|need to)\b", text) and re.search(r"\b(however|although)\b", text):
        return "argumentative"
    return "academic"


def analyze(model: DocumentModel) -> AnalysisResult:
    blocks = build_blocks(model)
    essay_type = _essay_type(model)
    setattr(model, "_essay_type", essay_type)

    findings: list[Finding] = []
    findings += front_matter_rules(model)
    findings += abstract_rules(model)
    if essay_type == "statement":
        findings += statement_rules(model, blocks)
    elif essay_type not in {"bibliography", "report", "reflection"}:
        findings += thesis_rules(model, blocks)
        findings += counterargument_rules(model, blocks)
    findings += body_rules(model, blocks)
    if essay_type not in {"bibliography", "report", "reflection"}:
        findings += conclusion_rules(model, blocks)
    findings += mechanics_rules(model)
    findings += reference_rules(model)
    from . import pedagogy
    findings += pedagogy.rhetoric(model, blocks)
    findings += pedagogy.mechanics(model, blocks)
    findings += pedagogy.formatting(model)

    seen: set[tuple] = set()
    unique: list[Finding] = []
    for f in findings:
        if f.end - f.start < 2:
            continue
        k = f.key()
        if k in seen:
            continue
        seen.add(k)
        unique.append(f)

    all_text = " ".join(p.text for p in model.body_paragraphs)
    metrics = {
        "word_count": model.word_count,
        "paragraphs": len(model.body_paragraphs),
        "blocks": len(blocks),
        "sentences": sum(len(split_sentences(p.text)) for p in model.body_paragraphs),
        "sources": len(_sources(all_text)),
        "citations": len(_citation_spans(all_text)),
    }
    return AnalysisResult(
        findings=unique,
        essay_type=essay_type,
        sources=_sources(all_text),
        metrics=metrics,
        blocks=blocks,
    )
