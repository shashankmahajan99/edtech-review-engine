"""Comment selection: turn raw findings into a professional review layout.

The human exemplars run 9-17 comments per manuscript, roughly one per 90 words,
spread across argument, mechanics and formatting.  Selection therefore:

* drops overlapping anchors and duplicate paragraphs,
* caps how many comments any one category can take,
* spends the budget on the highest-confidence findings first,
* guarantees rhetorical coverage when any rhetorical finding exists,
* orders the result by document position, as a reviewer would read it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from .analysis import (
    ABSTRACT, APA, CLARITY, CONCLUSION, COUNTER, EVIDENCE, FRAGMENTS, INFORMAL,
    INTRO, MLA, ORGANISATION, PUNCT, SVA, THESIS, TOPIC, TRANSITION, AnalysisResult,
    Finding,
)
from .docmodel import DocumentModel

# How many comments of each category a single review may contain.
CATEGORY_CAPS = {
    THESIS: 1,
    INTRO: 1,
    CONCLUSION: 1,
    ABSTRACT: 1,
    COUNTER: 1,
    MLA: 4,
    APA: 4,
    EVIDENCE: 2,
    TRANSITION: 2,
    TOPIC: 2,
    ORGANISATION: 2,
    PUNCT: 2,
    FRAGMENTS: 1,
    SVA: 1,
    INFORMAL: 1,
    CLARITY: 2,
}

RHETORICAL = {THESIS, INTRO, ORGANISATION, TOPIC, TRANSITION, EVIDENCE, CONCLUSION,
              COUNTER, ABSTRACT}

# Findings that must carry a category label in the comment body.
ALWAYS_LABELLED = RHETORICAL | {MLA, APA, PUNCT, FRAGMENTS, SVA, INFORMAL, CLARITY}

# Rules that should not repeat within one review even across paragraphs.
RULE_CAPS = {
    "mla_container_italics": 1,
    "mla_raw_url_container": 1,
    "implausible_year": 1,
    "apa_database": 1,
    "org_name_mismatch": 1,
    "works_cited_top_margin": 1,
    "counterargument_missing": 1,
    "thesis_missing": 1,
    "thesis_vague": 1,
    "thesis_no_preview": 1,
    "conclusion_summary": 1,
}


@dataclass
class SelectedComment:
    finding: Finding
    category: str
    labelled: bool


def _target_count(model: DocumentModel) -> int:
    words = model.word_count
    return max(7, min(18, round(words / 85) + 3))


def _overlaps(a: Finding, b: Finding) -> bool:
    if a.paragraph.index != b.paragraph.index:
        return False
    return a.start < b.end and b.start < a.end


MERGE_PAIRS = {
    (CONCLUSION, FRAGMENTS): "conclusion_and_fragments",
    (CONCLUSION, PUNCT): "conclusion_and_punctuation",
    (THESIS, SVA): "thesis_and_grammar",
}


def _premerge(findings: list[Finding]) -> list[Finding]:
    """Fold a paired mechanics finding into its rhetorical neighbour.

    The exemplars write a single note labelled "CONCLUSION AND FRAGMENTS" rather
    than two overlapping comments on the same sentence.
    """
    out: list[Finding] = []
    used: set[int] = set()
    ordered = sorted(findings, key=lambda f: (-f.priority, f.paragraph.index, f.start))
    for i, f in enumerate(ordered):
        if i in used:
            continue
        for (primary_cat, secondary_cat), rule in MERGE_PAIRS.items():
            if f.category != primary_cat:
                continue
            partner_idx = next(
                (j for j, g in enumerate(ordered)
                 if j != i and j not in used
                 and g.paragraph.index == f.paragraph.index
                 and g.category == secondary_cat
                 and _overlaps(f, g)),
                None,
            )
            if partner_idx is not None:
                partner = ordered[partner_idx]
                f.rule_id = rule
                f.category = f"{f.category} AND {partner.category}"
                f.priority = max(f.priority, partner.priority)
                used.add(partner_idx)
            break
        out.append(f)
    return out


def select_comments(model: DocumentModel, result: AnalysisResult) -> list[SelectedComment]:
    budget = _target_count(model)
    findings = sorted(_premerge(result.findings),
                      key=lambda f: (-f.priority, f.paragraph.index, f.start))

    chosen: list[Finding] = []
    per_category: dict[str, int] = {}
    per_paragraph: dict[int, int] = {}
    per_rule: dict[str, int] = {}

    def can_take(f: Finding) -> bool:
        if per_category.get(f.category, 0) >= CATEGORY_CAPS.get(f.category, 2):
            return False
        if per_rule.get(f.rule_id, 0) >= RULE_CAPS.get(f.rule_id, 2):
            return False
        # One comment per paragraph keeps the margin readable; long paragraphs
        # can carry a second note when the two anchors do not overlap.
        words = len(f.paragraph.words)
        limit = 2 if words <= 20 or words >= 35 else 1
        if per_paragraph.get(f.paragraph.index, 0) >= limit:
            return False
        if any(_overlaps(f, other) for other in chosen):
            return False
        return True

    for f in findings:
        if len(chosen) >= budget:
            break
        if can_take(f):
            chosen.append(f)
            per_category[f.category] = per_category.get(f.category, 0) + 1
            per_paragraph[f.paragraph.index] = per_paragraph.get(f.paragraph.index, 0) + 1
            per_rule[f.rule_id] = per_rule.get(f.rule_id, 0) + 1

    # Rhetorical coverage: if we have room and nothing rhetorical was chosen,
    # promote the strongest rhetorical finding even at the cost of mechanics.
    if budget > 6 and not any(f.category.split(" AND ")[0] in RHETORICAL for f in chosen):
        promoted = next((f for f in findings if f.category in RHETORICAL
                         and f.paragraph.index not in per_paragraph), None)
        if promoted is not None:
            dropped = next((f for f in reversed(chosen) if f.category not in RHETORICAL), None)
            if dropped is not None:
                chosen.remove(dropped)
            chosen.append(promoted)
            per_paragraph[promoted.paragraph.index] = 1

    chosen.sort(key=lambda f: (f.paragraph.index, f.start))

    selected: list[SelectedComment] = []
    for f in chosen:
        # Short formatting/mechanics comments read better without a label when
        # the exemplars show the same pattern; everything else is labelled.
        labelled = f.category in ALWAYS_LABELLED or f.priority >= 60
        selected.append(SelectedComment(f, f.category, labelled))
    return selected


def _merged_rule(primary: str, secondary: str) -> str:
    key = f"{primary}|{secondary}".lower().replace(" ", "_")
    return {
        "conclusion|fragments": "conclusion_and_fragments",
        "conclusion|punctuation": "conclusion_and_punctuation",
        "thesis_statement|subject-verb_agreement": "thesis_and_grammar",
    }.get(key, f"{primary.lower()}_and_{secondary.lower()}".replace(" ", "_"))
