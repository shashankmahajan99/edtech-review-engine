"""Deterministic 26-pattern structural scrubber and auditor.

Operates offline and deterministically on generated feedback prose.
Protects quoted student material and knowledge-base links before any substitution.
"""
from __future__ import annotations

import hashlib
import re

_URL_PATTERN = re.compile(r"https?://\S+")
_KEEP_MARKER_PATTERN = re.compile(r"\[\[KEEP_[^\]]+\]\]|HZ[0-9a-zA-Z]+X\d+Z")
_DOUBLE_QUOTE_PATTERN = re.compile(r'"[^"]*"')
_TYPO_DOUBLE_QUOTE_PATTERN = re.compile(r"“[^”]*”")
_TYPO_SINGLE_QUOTE_PATTERN = re.compile(r"‘(?:[^’]|(?<=\w)’(?=\w))*’")
_STRAIGHT_SINGLE_QUOTE_PATTERN = re.compile(r"(?<!\w)'(?:[^'\n]|(?<=\w)'(?=\w))*'(?!\w)")

# 26 Anti-AI Structural and Vocabulary Rules
# Pattern mapping: (compiled_regex_str, replacement_str, tell_name)
_BANNED_DISCOURSE: list[tuple[str, str, str]] = [
    # 1. Negative parallelisms ("Not X, but Y" / "Not only X, but also Y")
    (
        r"\b(?:this|it)\s+is\s+not\s+(?:just|merely|simply)\s+[^,;]+[,;]\s*(?:rather,\s*)?(?:it\s+is|it['’]s)\s+([^.!?]+)",
        r"It is \1",
        "not_x_but_y",
    ),
    (
        r"\bnot\s+only\s+([^,]+),\s*but\s+(?:also\s+)?([^\.!?]+)",
        r"\1, and \2",
        "not_only_but_also",
    ),
    # 2. Delve family
    (r"\bdelv(e|es|ing|ed)\s+into\b", r"examin\1", "delve_into"),
    (r"\bdelv(e|es|ing|ed)\b", r"examin\1", "delve"),
    # 3. Testament family
    (r"\bstands?\s+as\s+a\s+testament\s+to\b", "reflects", "testament_to"),
    (r"\b(?:a\s+)?testament\s+to\b", "evidence of", "testament"),
    (r"\btestament\b", "evidence", "testament"),
    # 4. Tapestry
    (r"\b(?:rich|complex|multifaceted|holistic)?\s*tapestry\s+of\b", "range of", "tapestry"),
    (r"\btapestry\b", "structure", "tapestry"),
    # 5. Beacon
    (r"\bbeacon\s+of\s+(?:hope|light|clarity)\b", "guide for", "beacon_of"),
    # 6. Paramount
    (r"\bis\s+of\s+paramount\s+importance\b", "is critical", "paramount_importance"),
    (r"\bparamount\b", "critical", "paramount"),
    # 7. Vital / crucial / pivotal role
    (r"\bplays?\s+a\s+(?:crucial|vital|pivotal)\s+role\s+in\b", "directly shapes", "vital_role"),
    (r"\b(?:crucial|vital|pivotal)\s+role\b", "key part", "vital_role"),
    # 8. Underscores
    (r"\bunderscores?\s+the\s+(?:importance|need)\s+(?:for|of)\b", "shows the need for", "underscores_need"),
    (r"\bunderscore(s|d|ing)?\b", r"show\1", "underscores"),
    # 9. Stacked qualifiers (Pattern 9)
    (r"\bcould\s+potentially\b", "can", "stacked_qualifiers"),
    (r"\bmight\s+possibly\b", "might", "stacked_qualifiers"),
    (r"\bmay\s+arguably\b", "may", "stacked_qualifiers"),
    # 10. Fast-paced world cliché
    (r"\bin\s+today['’]s\s+(?:fast-paced|modern|interconnected)\s+world\b", "today", "todays_fast_paced"),
    # 11. Leading discourse markers
    (r"^(Moreover|Furthermore|Additionally|Notably),?\s*", "Also, ", "leading_discourse"),
    # 12. Mid-sentence discourse markers
    (r"\b(moreover|furthermore|additionally|notably)\b", "also", "discourse_markers"),
    # 13. In conclusion / To summarize
    (r"^(In\s+conclusion|To\s+summarize),?\s*", "To close, ", "in_conclusion"),
    # 14. It is worth noting / crucial to remember
    (
        r"\bIt\s+is\s+(?:important|crucial|worth|essential)\s+(?:to\s+note|noting|to\s+remember)\s+that\s*",
        "Note that ",
        "important_to_note",
    ),
    (r"\bit\s+is\s+worth\s+noting\b", "Note", "important_to_note"),
    (r"\bit\s+is\s+crucial\s+to\s+remember\b", "Remember", "important_to_note"),
    # 15. Dynamic interplay
    (r"\b(?:dynamic\s+)?interplay\s+between\b", "relationship between", "interplay"),
    (r"\binterplay\b", "connection", "interplay"),
    # 16. Foster
    (r"\bfoster(s|ing|ed)?\b", r"build\1", "foster"),
    # 17. Copula avoidance (Pattern 18)
    (r"\b(?:serves\s+as|functions\s+as|stands\s+as)\s+a\b", "is a", "copula_avoidance"),
    (r"\b(?:serves\s+as|functions\s+as|stands\s+as)\b", "is", "copula_avoidance"),
    (r"\bboasts\s+a\b", "has a", "copula_avoidance"),
    (r"\bboasts\b", "has", "copula_avoidance"),
    # 18. Embark on
    (r"\bembark(s|ing|ed)?\s+on\b", r"start\1", "embarking"),
    # 19. Nuanced view
    (r"\bnuanced\s+(?:understanding|perspective|view)\b", "detailed understanding", "nuanced_view"),
    # 20. Holistic approach
    (r"\bholistic\s+(?:approach|view|perspective)\b", "complete approach", "holistic_approach"),
    # 21. Seamlessly
    (r"\bseamlessly\s+(integrates|connects|blends)\b", r"\1", "seamlessly"),
    (r"\bseamlessly\b", "smoothly", "seamlessly"),
    # 22. Navigating the complexities
    (r"\bnavigat(?:e|es|ing)\s+the\s+complexities\s+of\b", "working through", "navigating_complexities"),
    # 23. Sheds light on
    (r"\bsheds?\s+light\s+on\b", "clarifies", "sheds_light"),
    # 24. Document meta-reference (Pattern 25)
    (r"\bthis\s+(?:essay|paper|document)\s+(?:attempts|seeks|aims)\s+to\b", "you try to", "meta_reference"),
    (r"\bthe\s+(?:essay|paper|document)\s+(?:attempts|seeks|aims)\s+to\b", "your draft tries to", "meta_reference"),
]

# 25. Staged run-ups (Pattern 4)
_STAGED_RUNUPS = re.compile(
    r"^(?:Here['’]s\s+the\s+thing:|At\s+its\s+core,|Let['’]s\s+dive\s+in[,:]?|Honestly,)\s*",
    re.IGNORECASE,
)

# 26. Trailing shallow -ing riders at clause ends (Pattern 15)
_SHALLOW_ING_RIDERS = re.compile(
    r",\s*(?:highlighting|underscoring|showcasing|demonstrating|illustrating|emphasizing)\s+"
    r"(?:how|that|the\s+need|the\s+importance|your\s+argument|this\s+point)[^.!?]*([.!?])",
    re.IGNORECASE,
)

_CONTRACTION_EXPANSIONS = {
    "can't": "cannot",
    "won't": "will not",
    "don't": "do not",
    "doesn't": "does not",
    "didn't": "did not",
    "isn't": "is not",
    "aren't": "are not",
    "wasn't": "was not",
    "weren't": "were not",
    "hasn't": "has not",
    "haven't": "have not",
    "hadn't": "had not",
    "shouldn't": "should not",
    "couldn't": "could not",
    "wouldn't": "would not",
    "it's": "it is",
    "you're": "you are",
    "they're": "they are",
    "we're": "we are",
    "that's": "that is",
    "there's": "there is",
    "here's": "here is",
    "what's": "what is",
    "who's": "who is",
    "let's": "let us",
    "i'm": "I am",
    "you'll": "you will",
    "they'll": "they will",
    "we'll": "we will",
    "it'll": "it will",
    "you've": "you have",
    "they've": "they have",
    "we've": "we have",
}
_CONTRACTION_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(k).replace("'", "['’]") for k in _CONTRACTION_EXPANSIONS)
    + r")\b",
    re.IGNORECASE,
)

_SEEDED_CONTRACTION_PAIRS = [
    (re.compile(r"\bdo\s+not\b", re.IGNORECASE), "don't"),
    (re.compile(r"\bdoes\s+not\b", re.IGNORECASE), "doesn't"),
    (re.compile(r"\bis\s+not\b", re.IGNORECASE), "isn't"),
    (re.compile(r"\bare\s+not\b", re.IGNORECASE), "aren't"),
    (re.compile(r"\bcannot\b", re.IGNORECASE), "can't"),
    (re.compile(r"\bwill\s+not\b", re.IGNORECASE), "won't"),
    (re.compile(r"\byou\s+will\b", re.IGNORECASE), "you'll"),
    (re.compile(r"\bit\s+is\b", re.IGNORECASE), "it's"),
]


def _expand_contractions(text: str) -> str:
    """Expand English contractions to full forms (0% contraction corpus standard)."""
    def _repl(match: re.Match) -> str:
        token = match.group(0)
        expanded = _CONTRACTION_EXPANSIONS[token.lower().replace("’", "'")]
        return expanded[0].upper() + expanded[1:] if token[0].isupper() else expanded

    return _CONTRACTION_RE.sub(_repl, text)


def _inject_seeded_contractions(text: str, seed: int | str, rate: float = 0.70) -> str:
    """Deterministically contract common pairs at ~rate outside quotes when requested."""
    occ = 0

    for pattern, contracted in _SEEDED_CONTRACTION_PAIRS:
        def _repl(match: re.Match) -> str:
            nonlocal occ
            occ += 1
            digest = hashlib.sha1(f"{seed}:{occ}:{match.group(0).lower()}".encode("utf-8")).digest()
            roll = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
            if roll <= rate:
                orig = match.group(0)
                return contracted[0].upper() + contracted[1:] if orig[0].isupper() else contracted
            return match.group(0)

        text = pattern.sub(_repl, text)
    return text


def _case_preserving_sub(pattern: str, replacement: str, text: str) -> str:
    """Apply case-insensitive regex replacement while preserving leading uppercase."""
    def _repl(match: re.Match) -> str:
        out = match.expand(replacement)
        if out and match.group(0) and match.group(0)[0].isupper():
            return out[0].upper() + out[1:]
        return out

    return re.sub(pattern, _repl, text, flags=re.IGNORECASE)


def _mask_protected_spans(text: str) -> tuple[str, dict[str, str]]:
    """Mask URLs, humanizer nonces, and quoted student spans using unique nonces."""
    spans: dict[str, str] = {}
    counter = 0

    def replace_span(match: re.Match) -> str:
        nonlocal counter
        nonce = f"__PROTECTED_SPAN_{counter}__"
        counter += 1
        spans[nonce] = match.group(0)
        return nonce

    masked = _URL_PATTERN.sub(replace_span, text)
    masked = _KEEP_MARKER_PATTERN.sub(replace_span, masked)
    masked = _DOUBLE_QUOTE_PATTERN.sub(replace_span, masked)
    masked = _TYPO_DOUBLE_QUOTE_PATTERN.sub(replace_span, masked)
    masked = _TYPO_SINGLE_QUOTE_PATTERN.sub(replace_span, masked)
    masked = _STRAIGHT_SINGLE_QUOTE_PATTERN.sub(replace_span, masked)

    return masked, spans


def _unmask_protected_spans(text: str, spans: dict[str, str]) -> str:
    """Restore masked protected spans byte-for-byte."""
    for nonce, orig in spans.items():
        text = text.replace(nonce, orig)
    return text


def scrub_ai_tells(
    text: str,
    seed: int | str = 0,
    contraction_mode: str = "expand",
) -> str:
    """Deterministically eliminate structural AI tells outside student quotes and URLs.

    Parameters
    ----------
    text:
        Feedback comment or endnote paragraph to scrub.
    seed:
        Deterministic seed derived from document fingerprint / rule / position.
    contraction_mode:
        ``"expand"`` (default) enforces the 0% contraction corpus standard
        required by ``tests/test_feedback_humanizer.py`` and ``docs/ANTI_AI_PRACTICES.md``.
        ``"seeded"`` deterministically injects natural contractions at ~70% rate
        outside quoted spans.
    """
    if not text:
        return text

    masked, spans = _mask_protected_spans(text)

    # 1. Strip staged run-ups (Pattern 4)
    masked = _STAGED_RUNUPS.sub("", masked)

    # 2. Trailing shallow -ing riders at clause ends (Pattern 15)
    masked = _SHALLOW_ING_RIDERS.sub(r"\1", masked)

    # 3. Apply all structural & lexical patterns
    for pattern, replacement, _ in _BANNED_DISCOURSE:
        masked = _case_preserving_sub(pattern, replacement, masked)

    # 4. Handle contractions deterministically outside quotes
    if contraction_mode == "seeded":
        masked = _inject_seeded_contractions(masked, seed=seed)
    elif contraction_mode == "expand":
        masked = _expand_contractions(masked)

    # Clean double spaces and stray punctuation spaces before restoration
    masked = re.sub(r"[ \t]{2,}", " ", masked)
    masked = re.sub(r"\s+([,.;!?])", r"\1", masked)

    return _unmask_protected_spans(masked, spans).strip()


def audit_ai_tells(text: str) -> list[str]:
    """Audit unquoted feedback prose for any remaining 26-pattern AI tells."""
    if not text:
        return []

    masked, _ = _mask_protected_spans(text)
    tells: list[str] = []

    if _STAGED_RUNUPS.search(masked):
        tells.append("staged_runups")

    if _SHALLOW_ING_RIDERS.search(masked):
        tells.append("shallow_ing_riders")

    for pattern, _, tell_name in _BANNED_DISCOURSE:
        if re.search(pattern, masked, re.IGNORECASE):
            tells.append(tell_name)

    return sorted(set(tells))
