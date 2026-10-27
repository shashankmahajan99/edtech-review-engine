"""Loader for the ThinkingStorm-aligned review knowledge base (v2).

The KB is rule data: 22 rhetorical moves, 88 reusable comment patterns, 120
diagnostics, banned vocabulary and an endnote template.  This module maps our
detected rules onto the KB's moves and fills pattern slots only from facts that
are actually present in the student's draft; a pattern with an unresolved slot is
skipped, never guessed.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
KB_PATH = ROOT / "knowledge" / "thinkingstorm_kb_v2.json"

MOVE_BY_RULE = {
    "thesis_vague": "thesis",
    "thesis_no_preview": "thesis",
    "thesis_missing": "thesis",
    "thesis_spread": "thesis",
    "thesis_rhetorical_missing": "thesis",
    "thesis_and_grammar": "thesis",
    "intro_generic": "introduction",
    "abstract_intro": "abstract",
    "evidence_no_analysis": "analysis",
    "study_listing": "analysis",
    "statistics_no_analysis": "statistics",
    "transition_abrupt": "transitions",
    "topic_evidence_opener": "topic_sentences",
    "paragraph_overlong": "organization",
    "para_drift": "organization",
    "repeated_opener": "organization",
    "org_name_mismatch": "organization",
    "conclusion_summary": "conclusion",
    "conclusion_thin": "conclusion",
    "conclusion_announced": "conclusion",
    "conclusion_and_fragments": "conclusion",
    "conclusion_and_punctuation": "conclusion",
    "comma_splice": "grammar",
    "fragment": "grammar",
    "subject_verb": "grammar",
    "double_period": "grammar",
    "space_before_punct": "grammar",
    "missing_space_after_punct": "grammar",
    "citation_period_space": "grammar",
    "typo_cluster": "grammar",
    "typo_spacing": "grammar",
    "implausible_year": "grammar",
    "informal_diction": "clarity",
    "wordiness": "clarity",
    "vague_pronoun": "clarity",
    "para_filler": "clarity",
    "para_monotone": "clarity",
    "para_passive": "clarity",
    "quote_no_page": "evidence",
    "para_unsupported": "evidence",
    "para_no_claim": "topic_sentences",
    "counterargument_missing": "logic",
    "mla_header_missing": "mla",
    "mla_heading_order": "mla",
    "mla_heading_same_line": "mla",
    "mla_title_case": "mla",
    "mla_date_numeric": "mla",
    "mla_container_italics": "mla",
    "mla_raw_url_container": "mla",
    "works_cited_top_margin": "mla",
    "apa_course_name": "apa",
    "apa_database": "apa",
    "apa_date_numeric": "apa",
    "apa_instructor_missing": "apa",
    "statement_cliche_opener": "genre",
    "statement_generic_claim": "genre",
    "statement_no_specific_fit": "genre",
    "title_period": "formatting",
}

_STRENGTH = {"strength", "positive"}

# Legacy KB patterns predate rule bindings. Approve exact observations here;
# new patterns can declare their own `rules` metadata. Text edits require review.
_APPROVED_OBSERVATIONS = {
    "intro_generic": {"The opening about {topic} is a little broad."},
}


@lru_cache(maxsize=1)
def load() -> dict | None:
    if not KB_PATH.exists():
        return None
    try:
        return json.loads(KB_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def banned_phrases() -> list[str]:
    data = load()
    return list(data.get("banned_phrases", [])) if data else []


def persona() -> dict:
    data = load()
    return data.get("persona", {}) if data else {}


def anti_ai_rules() -> list[str]:
    data = load()
    return list(data.get("anti_ai_rules", [])) if data else []


def endnote_template() -> dict:
    data = load()
    return data.get("endnote_template", {}) if data else {}


def _short(text: str, words: int = 12) -> str:
    parts = text.split()
    if len(parts) <= words:
        return text.strip()
    return " ".join(parts[:words]).rstrip(".,;:") + "\u2026"


def _keywords(text: str, limit: int = 2) -> list[str]:
    from .segmenter import content_words

    seen: list[str] = []
    for word in content_words(text):
        low = word.lower()
        if low not in seen and len(low) >= 4:
            seen.append(low)
        if len(seen) >= limit:
            break
    return seen


def facts_for(model, finding) -> dict[str, str]:
    """Facts the KB slots may use, derived only from the student's draft.

    Conservative on purpose: a slot is filled only when the value is clean
    enough to read naturally (a real title, a citation, a number, the detected
    term).  Keyword guessing produced lines like "discusses occurs and bacteria",
    so point/other_point/claim are left empty and those patterns are skipped.
    """
    facts: dict[str, str] = {}
    quote = _short((finding.quote or "").strip(), 12)
    if quote:
        facts["anchor"] = f"\u201c{quote}\u201d"
        facts["quote"] = f"\u201c{quote}\u201d"

    title = next((p.text.strip(" .:") for p in model.paragraphs if p.region == "title"), "")
    if title and len(title.split()) <= 8:
        facts["topic"] = title

    stat = re.search(r"\b\d+(?:\.\d+)?%?\b", finding.paragraph.text)
    if stat:
        facts["value"] = stat.group(0)
        facts["measure"] = stat.group(0)

    source = re.search(r"\(([A-Z][A-Za-z.&' -]{2,40}),?\s*(?:19|20)\d{2}", finding.paragraph.text)
    if source:
        facts["source"] = source.group(1).strip()
    elif finding.facts.get("source"):
        value = finding.facts["source"]
        facts["source"] = str(value[0] if isinstance(value, list) else value).strip()

    if finding.facts.get("term"):
        facts["term"] = str(finding.facts["term"]).strip()
    if finding.facts.get('vague'):
        facts['vague'] = ' and '.join('“' + str(term) + '”' for term in finding.facts['vague'][:2])

    facts["grammar_feature"] = finding.category.lower()
    if model.style and model.style != "auto":
        facts["style"] = model.style.upper()
    genre = getattr(model, "essay_type", "") or ""
    if genre:
        facts["genre"] = genre.replace("_", " ")

    return {k: v for k, v in facts.items() if v}


CONCRETE_SLOTS = {"anchor", "quote", "source", "topic", "term", "value",
                  "measure", "style", "genre", "grammar_feature", "vague"}

# KB patterns are written per rhetorical move, not per diagnostic.  For citation
# and mechanics moves they can contradict the specific rule (an "indentation"
# pattern attached to a missing-instructor finding), so those keep the local,
# rule-specific templates only.
SAFE_MOVES = {
    "thesis", "introduction", "abstract", "evidence", "analysis", "statistics",
    "transitions", "topic_sentences", "organization", "conclusion", "clarity",
    "logic", "genre",
}


def patterns_for_rule(rule: str, model, finding) -> tuple[list[tuple[str, str]], list[tuple[str, str]]]:
    """Explicitly rule-bound KB patterns, split into specific and generic.

    Patterns must declare the diagnostic rules they support. Having slots that
    can be filled does not establish that a pattern's diagnosis is true.
    """
    data = load()
    if not data:
        return [], []
    move_id = MOVE_BY_RULE.get(rule)
    if not move_id or move_id not in SAFE_MOVES:
        return [], []
    move = next((m for m in data.get("moves", []) if m.get("id") == move_id), None)
    if not move:
        return [], []
    facts = facts_for(model, finding)
    specific: list[tuple[str, str]] = []
    generic: list[tuple[str, str]] = []
    for pattern in move.get("patterns", []):
        observation = pattern.get("observation", "")
        # Sharing a category does not establish the diagnosis. A conclusion
        # pattern about a new idea cannot describe a finding about repetition.
        if (rule not in pattern.get("rules", [])
                and observation not in _APPROVED_OBSERVATIONS.get(rule, set())):
            continue
        if str(pattern.get("intent", "issue")).lower() in _STRENGTH:
            continue
        advice = pattern.get("advice", "")
        slots = set(pattern.get("required_slots") or
                    re.findall(r"\{([^{}]+)\}", observation + advice))
        if not slots.issubset(facts):
            continue
        try:
            obs = observation.format(**facts).strip()
            adv = advice.format(**facts).strip() if advice else ""
        except (KeyError, ValueError, IndexError):
            continue
        if "{" in obs + adv or "}" in obs + adv:
            continue
        target = specific if slots & CONCRETE_SLOTS else generic
        target.append((obs, adv))
    return specific, generic
