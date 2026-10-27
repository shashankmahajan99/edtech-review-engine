"""Deterministic editorial style checks.

These checks describe readability and repetition. They do not measure
authorship, predict a third-party detector result, or certify human writing:

* no banned LLM vocabulary,
* sentence-length variance inside a human band,
* no repeated 5-gram across comments,
* varied sentence openers.

The reviewer exemplars provide a reference for readability thresholds.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .persona import BANNED_PHRASES

MIN_BURSTINESS_STD = 2.6
MAX_MEAN_SENTENCE = 32.0
MAX_NGRAM_REPEAT = 0.12
MIN_UNIQUE_OPENERS = 0.65


@dataclass
class StyleReport:
    ok: bool
    errors: list[str]
    metrics: dict


def sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", re.sub(r"\s+", " ", text).strip())
    return [p for p in parts if p.strip()]


def burstiness(text: str) -> tuple[float, float]:
    lengths = [len(s.split()) for s in sentences(text)]
    if len(lengths) < 2:
        return (0.0, 0.0)
    mean = sum(lengths) / len(lengths)
    var = sum((x - mean) ** 2 for x in lengths) / len(lengths)
    return (mean, var ** 0.5)


def _strip_quotes_and_urls(text: str) -> str:
    prose = re.sub(r"https?://\S+", " ", text)
    prose = re.sub(r"\u201c[^\u201d]*\u201d", " ", prose)
    prose = re.sub(r'"[^"]*"', " ", prose)
    prose = re.sub(r"‘(?:[^’]|(?<=\w)’(?=\w))*’", " ", prose)
    prose = re.sub(r"(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w))*'(?!\w)", " ", prose)
    return prose


def repeated_ngram_ratio(texts: list[str], n: int = 5) -> float:
    grams: dict[tuple[str, ...], int] = {}
    total = 0
    for text in texts:
        prose = _strip_quotes_and_urls(text)
        words = re.findall(r"[a-z']+", prose.lower())
        if len(words) < n:
            continue
        for i in range(len(words) - n + 1):
            gram = tuple(words[i:i + n])
            grams[gram] = grams.get(gram, 0) + 1
            total += 1
    if not total:
        return 0.0
    repeats = sum(count - 1 for count in grams.values() if count > 1)
    return repeats / total


def opener_ratio(texts: list[str]) -> float:
    openers = []
    for text in texts:
        first = sentences(text)
        if first:
            openers.append(" ".join(re.findall(r"[a-z']+", first[0].lower())[:3]))
    if not openers:
        return 1.0
    return len(set(openers)) / len(openers)


def banned_hits(text: str) -> list[str]:
    """LLM vocabulary in reviewer prose, ignoring quoted student specimens."""
    import re as _re

    prose = _re.sub(r"\u201c[^\u201d]*\u201d", " ", text)
    prose = _re.sub(r'"[^"]*"', " ", prose)
    prose = _re.sub(r"‘(?:[^’]|(?<=\w)’(?=\w))*’", " ", prose)
    prose = _re.sub(r"(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w))*'(?!\w)", " ", prose)
    low = prose.lower()
    return [p for p in BANNED_PHRASES if p in low]


def check_text_block(texts: list[str], label: str = "comments") -> StyleReport:
    errors: list[str] = []
    joined = " ".join(texts)
    mean, std = burstiness(joined)
    ngram = repeated_ngram_ratio(texts)
    openers = opener_ratio(texts)

    hits: list[str] = []
    for text in texts:
        hits.extend(banned_hits(text))
    if hits:
        errors.append(f"{label}: banned AI phrasing {sorted(set(hits))}")
    # Sentence-length variance is noisy on very short reviews; scale the bar.
    threshold = MIN_BURSTINESS_STD if len(texts) >= 6 else (1.6 if len(texts) >= 4 else 0.0)
    if len(texts) >= 3 and std < threshold:
        errors.append(f"{label}: sentence lengths too uniform (std {std:.1f} < {threshold})")
    if mean > MAX_MEAN_SENTENCE:
        errors.append(f"{label}: average sentence too long ({mean:.1f} words)")
    if len(texts) >= 3 and ngram > MAX_NGRAM_REPEAT:
        errors.append(f"{label}: repeated 5-grams {ngram:.2f} > {MAX_NGRAM_REPEAT}")
    if len(texts) >= 4 and openers < MIN_UNIQUE_OPENERS:
        errors.append(f"{label}: sentence openers repeat too often ({openers:.2f})")

    cv = round(std / mean, 3) if mean > 0 else 0.0

    return StyleReport(
        ok=not errors,
        errors=errors,
        metrics={
            "mean_sentence": round(mean, 2),
            "burstiness_std": round(std, 2),
            "cv": cv,
            "ngram_repeat": round(ngram, 3),
            "unique_openers": round(openers, 2),
            "banned": sorted(set(hits)),
        },
    )
