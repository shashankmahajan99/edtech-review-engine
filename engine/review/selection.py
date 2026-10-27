"""Comment selection: turn raw findings into a professional review layout.

The requested review density is 3–4 supported comments per page, spread across
argument, mechanics and formatting. Selection therefore:

* drops overlapping anchors and duplicate paragraphs,
* caps how many comments any one category can take,
* spends the budget on the highest-confidence findings first,
* guarantees rhetorical coverage when any rhetorical finding exists,
* orders the result by document position, as a reviewer would read it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace

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
    "paragraph_overlong": 2,
    "informal_diction": 1,
    "reference_alphabetical": 1,
    "reference_hanging_indent": 1,
    "reference_heading_style": 1,
    "mla_article_title_format": 2,
    "intro_concrete_context": 1,
    'acronym_case': 1,
    'front_double_spacing': 1,
    'apa_locator_hash': 2,
}


@dataclass
class SelectedComment:
    finding: Finding
    category: str
    labelled: bool


def _target_count(model: DocumentModel, comprehensive: bool = False) -> int:
    words = model.word_count
    if comprehensive:
        from .coverage import page_map
        return min(120, max(4, len(page_map(model).pages) * 4))
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
    # Selection must not rewrite the analysis used by the report or a later pass.
    ordered = sorted((replace(f, facts=dict(f.facts)) for f in findings),
                     key=lambda f: (-f.priority, f.paragraph.index, f.start))
    for i, f in enumerate(ordered):
        if i in used:
            continue
        if f.rule_id not in {'conclusion_summary', 'conclusion_thin', 'thesis_vague', 'thesis_no_preview', 'thesis_missing'}:
            out.append(f)
            used.add(i)
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
        used.add(i)
    return out


def select_comments(model: DocumentModel, result: AnalysisResult,
                    comprehensive: bool = False) -> list[SelectedComment]:
    budget = _target_count(model, comprehensive)
    findings = sorted(_premerge(result.findings),
                      key=lambda f: (-f.priority, f.paragraph.index, f.start))

    chosen: list[Finding] = []
    per_category: dict[str, int] = {}
    per_paragraph: dict[int, int] = {}
    per_rule: dict[str, int] = {}
    from .coverage import page_map
    pages = page_map(model)
    per_page: dict[int, int] = {}

    def can_take(f: Finding) -> bool:
        if comprehensive and per_page.get(pages.page_for(f), 0) >= 4:
            return False
        cap = CATEGORY_CAPS.get(f.category, 2)
        if comprehensive and f.category not in {THESIS, CONCLUSION, ABSTRACT, COUNTER, INTRO}:
            cap = max(cap + 2, len(pages.pages))
        if comprehensive and f.category in {MLA, APA}:
            cap = 10
        if per_category.get(f.category, 0) >= cap:
            return False
        rule_cap = RULE_CAPS.get(f.rule_id, 2)
        if comprehensive and f.rule_id not in RULE_CAPS:
            rule_cap = max(3, len(pages.pages))
        if per_rule.get(f.rule_id, 0) >= rule_cap:
            return False
        # A full review annotates the paragraph, not just the document: permit
        # up to three notes on a substantial paragraph when they do not overlap.
        words = len(f.paragraph.words)
        limit = min(6, max(3, (words + 79) // 80 + 1)) if comprehensive and words >= 45 else (2 if words <= 20 or words >= 35 else 1)
        if per_paragraph.get(f.paragraph.index, 0) >= limit:
            return False
        if any(_overlaps(f, other) for other in chosen):
            return False
        return True

    def take(f):
        chosen.append(f)
        per_category[f.category] = per_category.get(f.category, 0) + 1
        per_paragraph[f.paragraph.index] = per_paragraph.get(f.paragraph.index, 0) + 1
        per_rule[f.rule_id] = per_rule.get(f.rule_id, 0) + 1
        page = pages.page_for(f)
        per_page[page] = per_page.get(page, 0) + 1

    if comprehensive:
        # Reserve a supported note for each logical body block before spending
        # the remaining page budget on extra formatting or repeat corrections.
        for block in result.blocks:
            if len(chosen) >= budget:
                break
            ids = {p.index for p in block.paragraphs}
            candidate = next((f for f in findings if f.paragraph.index in ids and can_take(f)), None)
            if candidate is not None:
                take(candidate)

    for f in findings:
        if len(chosen) >= budget:
            break
        if can_take(f):
            take(f)

    if comprehensive:
        # Coverage pass: every body block with a finding gets up to two notes,
        # so the review reads as a full margin rather than a sample.
        chosen_ids = {id(f) for f in chosen}
        block_of: dict[int, int] = {}
        for bi, block in enumerate(result.blocks):
            for paragraph in block.paragraphs:
                block_of[paragraph.index] = bi
        for block in result.blocks:
            paragraph_ids = {p.index for p in block.paragraphs}
            candidates = [f for f in findings
                          if f.paragraph.index in paragraph_ids and id(f) not in chosen_ids]
            candidates.sort(key=lambda f: -f.priority)
            added = 0
            for finding in candidates:
                if added >= 2 or len(chosen) >= budget:
                    break
                if can_take(finding):
                    chosen.append(finding)
                    chosen_ids.add(id(finding))
                    per_category[finding.category] = per_category.get(finding.category, 0) + 1
                    per_paragraph[finding.paragraph.index] = per_paragraph.get(finding.paragraph.index, 0) + 1
                    per_rule[finding.rule_id] = per_rule.get(finding.rule_id, 0) + 1
                    page = pages.page_for(finding)
                    per_page[page] = per_page.get(page, 0) + 1
                    added += 1

    if comprehensive:
        # Strict density: every page must reach the requested minimum, not just
        # the maximum. Fill from findings already present on that page; this
        # pass relaxes category/rule caps but keeps non-overlap and the 4/page
        # hard cap.
        from .coverage import PROFILE
        minimum = PROFILE['requested_comments_per_page']['min']
        maximum = PROFILE['requested_comments_per_page']['max']
        chosen_ids = {id(f) for f in chosen}
        for page in sorted(set(pages.pages) | set(per_page)):
            while per_page.get(page, 0) < minimum:
                candidate = next(
                    (f for f in findings
                     if id(f) not in chosen_ids
                     and pages.page_for(f) == page
                     and per_page.get(page, 0) < maximum
                     and not any(_overlaps(f, other) for other in chosen)),
                    None,
                )
                if candidate is None:
                    break
                chosen.append(candidate)
                chosen_ids.add(id(candidate))
                per_category[candidate.category] = per_category.get(candidate.category, 0) + 1
                per_paragraph[candidate.paragraph.index] = per_paragraph.get(candidate.paragraph.index, 0) + 1
                per_rule[candidate.rule_id] = per_rule.get(candidate.rule_id, 0) + 1
                per_page[page] = per_page.get(page, 0) + 1

    # Rhetorical coverage: if we have room and nothing rhetorical was chosen,
    # promote the strongest rhetorical finding even at the cost of mechanics.
    if not comprehensive and budget > 6 and not any(f.category.split(" AND ")[0] in RHETORICAL for f in chosen):
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
