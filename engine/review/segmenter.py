"""Offset-preserving sentence segmentation.

Word text is deliberately not normalised: every returned span indexes directly
into ``Paragraph.text`` so it can be used verbatim as a comment anchor.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# Abbreviations whose trailing period must not end a sentence.
_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "vs", "etc", "e.g", "i.e",
    "cf", "ibid", "vol", "no", "pp", "p", "ed", "eds", "inc", "ltd", "co", "univ",
    "dept", "fig", "al", "approx", "jan", "feb", "mar", "apr", "jun", "jul", "aug",
    "sep", "sept", "oct", "nov", "dec", "mt", "ft", "gen", "col", "lt", "sgt",
}

_URL_RE = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
_DECIMAL_RE = re.compile(r"\d\.\d")
_INITIAL_RE = re.compile(r"(?<![\w.])[A-Z]\.")

# A closing quote/bracket may follow the terminal punctuation.
_CLOSERS = "\"')\u201d\u2019]}"


@dataclass(frozen=True)
class Sentence:
    start: int
    end: int
    text: str

    @property
    def words(self) -> list[str]:
        return self.text.split()


def _protected_positions(text: str) -> set[int]:
    protected: set[int] = set()

    for m in _URL_RE.finditer(text):
        protected.update(range(m.start(), m.end()))
    for m in _DECIMAL_RE.finditer(text):
        protected.add(m.start() + 1)
    for m in _INITIAL_RE.finditer(text):
        protected.add(m.end() - 1)

    for m in re.finditer(r"[A-Za-z][A-Za-z.]*\.", text):
        token = m.group(0).lower().rstrip(".")
        if token in _ABBREVIATIONS:
            protected.add(m.end() - 1)
            continue
        # "et al." style
        if token.endswith(" al") or token == "al":
            protected.add(m.end() - 1)

    # Ellipses: dots inside "..." never terminate a sentence.
    for m in re.finditer(r"\.{2,}", text):
        protected.update(range(m.start(), m.end()))
    return protected


def split_sentences(text: str, min_chars: int = 12) -> list[Sentence]:
    """Split ``text`` into sentence spans, preserving exact offsets."""
    if not text.strip():
        return []

    protected = _protected_positions(text)
    boundaries: list[int] = []

    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch == "\n":
            boundaries.append(i + 1)
            i += 1
            continue
        if ch in ".!?" and i not in protected:
            j = i + 1
            while j < n and text[j] in _CLOSERS:
                j += 1
            if j >= n or text[j].isspace():
                boundaries.append(j)
                i = j
                continue
        i += 1

    spans: list[tuple[int, int]] = []
    prev = 0
    for b in boundaries:
        if b > prev:
            spans.append((prev, b))
            prev = b
    if prev < n:
        spans.append((prev, n))

    sentences: list[Sentence] = []
    for s, e in spans:
        raw = text[s:e]
        # trim surrounding whitespace while keeping offsets exact
        stripped = raw.strip()
        if not stripped:
            continue
        lead = len(raw) - len(raw.lstrip())
        start = s + lead
        end = start + len(stripped)
        sentences.append(Sentence(start, end, stripped))

    # Merge fragments that are too short to anchor meaningfully into the next one.
    merged: list[Sentence] = []
    carry: Sentence | None = None
    for sent in sentences:
        if carry is not None:
            start = carry.start
            end = sent.end
            carry = Sentence(start, end, text[start:end])
            if len(carry.text) >= min_chars:
                merged.append(carry)
                carry = None
            continue
        if len(sent.text) < min_chars and sent is not sentences[-1]:
            carry = sent
            continue
        merged.append(sent)
    if carry is not None:
        merged.append(carry)

    return merged


def sentence_containing(sentences: list[Sentence], pos: int) -> Sentence | None:
    for s in sentences:
        if s.start <= pos < s.end:
            return s
    return None


def first_sentence(text: str) -> Sentence | None:
    got = split_sentences(text)
    return got[0] if got else None


def last_sentence(text: str) -> Sentence | None:
    got = split_sentences(text)
    return got[-1] if got else None


_WORD_RE = re.compile(r"[A-Za-z][A-Za-z'\u2019-]+")


def content_words(text: str) -> list[str]:
    stop = {
        "the", "a", "an", "and", "or", "but", "if", "of", "to", "in", "on", "for",
        "with", "as", "at", "by", "from", "that", "this", "these", "those", "it",
        "is", "are", "was", "were", "be", "been", "being", "has", "have", "had",
        "do", "does", "did", "not", "no", "so", "than", "then", "there", "their",
        "they", "you", "your", "we", "our", "i", "my", "he", "she", "his", "her",
        "which", "who", "whom", "what", "when", "where", "why", "how", "can",
        "could", "should", "would", "may", "might", "must", "will", "shall",
        "about", "into", "over", "after", "before", "between", "through",
    }
    return [m.group(0).lower() for m in _WORD_RE.finditer(text) if m.group(0).lower() not in stop]
