"""Deterministic rubric, redline and executive summary from real findings.

This replaces the canned "3-pass" text in the portal.  Every score, verdict and
line edit is derived from what the analysis engine actually detected in the
manuscript, so the report, the tracked changes and the margin comments can never
disagree with one another.  No model is involved.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass

from .analysis import (
    ABSTRACT, ANALYSIS, APA, CLARITY, CONCLUSION, COUNTER, EVIDENCE, FRAGMENTS,
    INFORMAL, INTRO, MLA, ORGANISATION, PUNCT, STATISTICS, SVA, THESIS, TOPIC,
    TRANSITION, AnalysisResult, Finding,
)
from .docmodel import DocumentModel
from .endnote import compose_endnote
from .persona import human_date

PILLARS_ACADEMIC = [
    ("thesis_and_argumentation", "Thesis & Argumentation"),
    ("evidence_and_synthesis", "Evidence & Synthesis"),
    ("academic_voice_and_style", "Academic Voice & Style"),
    ("mechanics_and_citations", "Mechanics & Citations"),
]

PILLARS_ADMISSIONS = [
    ("narrative_hook_and_voice", "Narrative Hook & Voice"),
    ("intellectual_trajectory", "Intellectual Trajectory"),
    ("program_alignment", "Program Alignment"),
    ("narrative_economy_and_polish", "Narrative Economy & Polish"),
]

_ACADEMIC_MAP = {
    THESIS: "thesis_and_argumentation", INTRO: "thesis_and_argumentation",
    COUNTER: "thesis_and_argumentation", CONCLUSION: "thesis_and_argumentation",
    ORGANISATION: "thesis_and_argumentation", TOPIC: "thesis_and_argumentation",
    TRANSITION: "thesis_and_argumentation", ABSTRACT: "thesis_and_argumentation",
    EVIDENCE: "evidence_and_synthesis", STATISTICS: "evidence_and_synthesis",
    ANALYSIS: "evidence_and_synthesis",
    INFORMAL: "academic_voice_and_style", CLARITY: "academic_voice_and_style",
    PUNCT: "mechanics_and_citations", FRAGMENTS: "mechanics_and_citations",
    SVA: "mechanics_and_citations", MLA: "mechanics_and_citations",
    APA: "mechanics_and_citations",
}

_ADMISSIONS_MAP = {
    INTRO: "narrative_hook_and_voice", THESIS: "narrative_hook_and_voice",
    EVIDENCE: "intellectual_trajectory", ANALYSIS: "intellectual_trajectory",
    STATISTICS: "intellectual_trajectory",
    ORGANISATION: "program_alignment",
    INFORMAL: "narrative_economy_and_polish", CLARITY: "narrative_economy_and_polish",
    PUNCT: "narrative_economy_and_polish", FRAGMENTS: "narrative_economy_and_polish",
    SVA: "narrative_economy_and_polish", MLA: "narrative_economy_and_polish",
    APA: "narrative_economy_and_polish",
}

_VERDICTS = {
    "thesis_missing": "No sentence states a position; the opening describes the topic only.",
    "thesis_vague": "The thesis names the topic but not the argument it will prove.",
    "thesis_no_preview": "The thesis states a position but does not preview the body's points.",
    "thesis_spread": "The central claim is spread across several sentences instead of one.",
    "thesis_rhetorical_missing": "The introduction summarises the text but states no rhetorical thesis.",
    "intro_generic": "The opening is a general statement that could begin almost any essay.",
    "conclusion_summary": "The conclusion restates the body instead of drawing out an implication.",
    "conclusion_thin": "The closing paragraph lists points without synthesising them.",
    "conclusion_announced": "The ending is announced rather than earned.",
    "evidence_no_analysis": "Evidence is presented without an interpretation of what it proves.",
    "statistics_no_analysis": "A statistic is quoted without saying what it demonstrates.",
    "study_listing": "Studies are listed side by side rather than compared.",
    "transition_abrupt": "A paragraph opens a new line of thought without a bridge.",
    "paragraph_overlong": "A paragraph carries more than one idea.",
    "topic_evidence_opener": "A paragraph opens with evidence instead of a claim.",
    "repeated_opener": "Consecutive paragraphs open with the same construction.",
    "informal_diction": "Informal wording weakens the academic register.",
    "wordiness": "A phrase repeats an idea the sentence already made.",
    "vague_pronoun": "A sentence opens with a pronoun whose referent is unclear.",
    "subject_verb": "A sentence has a subject-verb agreement error.",
    "fragment": "A sentence is a fragment rather than a complete statement.",
    "typo_cluster": "Spacing and punctuation slips recur through the draft.",
    "space_before_punct": "Punctuation spacing needs correction.",
    "citation_period_space": "A period is separated from its citation.",
    "double_period": "A doubled period appears in the text.",
    "mla_date_numeric": "The MLA heading uses a numeric date.",
    "mla_heading_order": "The MLA heading lines are out of order.",
    "mla_heading_same_line": "Two MLA heading elements share one line.",
    "mla_title_case": "The title is not in MLA title case.",
    "mla_header_missing": "The running header with surname and page number is missing.",
    "mla_container_italics": "A container title is not italicised.",
    "mla_raw_url_container": "A raw URL stands in for the container title.",
    "apa_date_numeric": "The APA title page uses a numeric date.",
    "apa_instructor_missing": "The instructor line is missing from the title page.",
    "apa_course_name": "The course code appears without the course name.",
    "apa_database": "A database name is included where the DOI is sufficient.",
    "implausible_year": "A reference contains an implausible publication year.",
    "org_name_mismatch": "An organisation is named inconsistently between text and references.",
    "quote_no_page": "A direct quotation lacks a page reference.",
    "statement_cliche_opener": "The opening uses the standard lifelong-passion formula.",
    "statement_generic_claim": "Generic programme praise stands in for a specific reason.",
    "statement_no_specific_fit": "No specific course, lab, or faculty member is named.",
    "abstract_intro": "The abstract restates the introduction rather than summarising findings.",
    "counterargument_missing": "The argument never addresses its strongest objection.",
    "works_cited_top_margin": "Extra blank space precedes the Works Cited heading.",
    "para_unsupported": "A paragraph argues without bringing in a source.",
    "para_drift": "A paragraph opens on one claim and closes on another.",
    "para_filler": "A paragraph repeats the same filler word.",
    "para_monotone": "A paragraph's sentences are all the same length.",
    "para_passive": "A paragraph relies on passive constructions.",
    "para_no_claim": "A paragraph opens with a fact rather than a claim.",
}

_ACTIONS = {
    "thesis_missing": "Write one thesis sentence that states your position and previews the body.",
    "thesis_vague": "Rewrite the thesis to name the specific claim and the points that prove it.",
    "thesis_no_preview": "Add a preview of the body's points to the thesis sentence.",
    "thesis_spread": "Compress the scattered claims into one thesis sentence.",
    "thesis_rhetorical_missing": "State which rhetorical appeals the analysis will examine.",
    "intro_generic": "Open with a concrete moment instead of a general statement.",
    "conclusion_summary": "End on the implication of the argument rather than restating it.",
    "conclusion_thin": "Make the conclusion show how the points connect.",
    "evidence_no_analysis": "After each citation, add a sentence explaining what it proves.",
    "statistics_no_analysis": "Interpret the statistic before moving on.",
    "study_listing": "Compare the studies and state what they agree on.",
    "transition_abrupt": "Add a transition where the paragraph changes direction.",
    "paragraph_overlong": "Split the long paragraph where its focus shifts.",
    "subject_verb": "Fix the subject-verb agreement flagged in the margin.",
    "fragment": "Complete the fragment or attach it to the sentence it depends on.",
    "typo_cluster": "Proofread for the spacing and punctuation examples in the margin.",
    "informal_diction": "Replace the informal wording with the specific measure.",
    "wordiness": "Cut the wordy phrase flagged in the margin.",
    "vague_pronoun": "Name the noun the pronoun refers to.",
    "mla_date_numeric": "Spell the date out as day-month-year.",
    "mla_heading_order": "Reorder the heading: name, instructor, course, date.",
    "apa_date_numeric": "Write the date in words on the title page.",
    "apa_instructor_missing": "Add the instructor's name beneath the course line.",
    "apa_database": "Delete the database name; keep the DOI.",
    "mla_container_italics": "Italicise the container title.",
    "mla_raw_url_container": "Replace the URL with the site or journal title.",
    "statement_cliche_opener": "Open with the specific moment that made the field matter to you.",
    "statement_no_specific_fit": "Name two concrete courses, labs, or faculty and connect them to your work.",
    "statement_generic_claim": "Replace generic praise with a concrete programme detail.",
    "counterargument_missing": "Add and answer the strongest objection to your claim.",
    "quote_no_page": "Add the page number to the quotation.",
    "para_unsupported": "Add a source to the paragraph that argues without one.",
    "para_drift": "Return to the opening claim at the end of the paragraph.",
    "para_filler": "Cut the repeated filler word.",
    "para_monotone": "Vary sentence length in the flagged paragraph.",
    "para_passive": "Convert the passive constructions to active verbs.",
    "para_no_claim": "Open the paragraph with the claim, not the fact.",
}

_MAJOR_RULES = {
    "thesis_missing", "thesis_rhetorical_missing", "conclusion_summary",
    "statement_cliche_opener", "statement_no_specific_fit",
}


def _pillar_of(finding: Finding, mode: str) -> str:
    if finding.rule_id.startswith("statement_"):
        if finding.rule_id == "statement_no_specific_fit":
            return "program_alignment" if mode == "admissions" else "thesis_and_argumentation"
        return "narrative_hook_and_voice" if mode == "admissions" else "academic_voice_and_style"
    mapping = _ADMISSIONS_MAP if mode == "admissions" else _ACADEMIC_MAP
    return mapping.get(finding.category, "academic_voice_and_style" if mode != "admissions" else "narrative_economy_and_polish")


def _penalty(finding: Finding) -> int:
    if finding.rule_id in _MAJOR_RULES or finding.priority >= 84:
        return 4
    if finding.priority >= 70:
        return 3
    if finding.priority >= 60:
        return 2
    return 1


def _score_pillars(result: AnalysisResult, mode: str) -> dict[str, dict]:
    pillars = PILLARS_ADMISSIONS if mode == "admissions" else PILLARS_ACADEMIC
    grouped: dict[str, list[Finding]] = {key: [] for key, _label in pillars}
    for finding in result.findings:
        grouped.setdefault(_pillar_of(finding, mode), []).append(finding)

    scores: dict[str, dict] = {}
    for key, _label in pillars:
        issues = sorted(grouped.get(key, []), key=lambda f: -f.priority)
        penalty = min(8, sum(_penalty(f) for f in issues))
        score = max(17, 25 - penalty)
        if issues:
            verdict = _VERDICTS.get(issues[0].rule_id, "The margin comments identify the specific revisions.")
            if len(issues) > 1:
                verdict += f" ({len(issues)} notes in this domain.)"
        else:
            verdict = "No gaps detected in this domain during this pass."
        scores[key] = {"score": score, "max": 25, "verdict": verdict, "label": _label}
    return scores


def _summary(model: DocumentModel, result: AnalysisResult, scores: dict[str, dict],
             mode: str) -> str:
    from .selection import RHETORICAL

    ordered = sorted(scores.items(), key=lambda kv: kv[1]["score"])
    weakest, strongest = ordered[0], ordered[-1]
    label = dict(PILLARS_ADMISSIONS if mode == "admissions" else PILLARS_ACADEMIC)
    rhetorical = [f for f in result.findings if f.category in RHETORICAL]
    top = max(rhetorical or result.findings, key=lambda f: f.priority) if result.findings else None
    detail = ""
    if top is not None:
        detail = " The first revision is concrete: " + _ACTIONS.get(
            top.rule_id, "address the note anchored at the flagged sentence."
        ).capitalize()

    digest = int(hashlib.sha1(model.fingerprint.encode("utf-8")).hexdigest(), 16)
    blocks = result.metrics.get("blocks") or len(model.body_paragraphs)
    openers = [
        f"Reviewed {model.word_count} words across {blocks} body paragraphs.",
        f"This is a {model.word_count}-word draft with {blocks} body paragraphs.",
    ]
    body = (
        f" {label[strongest[0]]} is the strongest domain at {strongest[1]['score']}/25, "
        f"while {label[weakest[0]]} needs the most work at {weakest[1]['score']}/25."
    )
    if strongest[1]["score"] == weakest[1]["score"]:
        body = f" No domain stands out as a strength; each sits near {strongest[1]['score']}/25."
    return openers[digest % len(openers)] + body + detail


def _actions(result: AnalysisResult) -> list[str]:
    from .selection import RHETORICAL

    chosen: list[str] = []
    seen_families: set[str] = set()
    ordered = sorted(
        result.findings,
        key=lambda f: (0 if f.category in RHETORICAL else 1, -f.priority),
    )
    for finding in ordered:
        action = _ACTIONS.get(finding.rule_id)
        if not action:
            continue
        family = finding.rule_id.split("_")[0]
        if family in seen_families:
            continue
        if action in chosen:
            continue
        chosen.append(action)
        seen_families.add(family)
        if len(chosen) == 4:
            break
    if not chosen:
        chosen = ["No structural revisions are required; keep the current organisation."]
    return chosen


# ---------------------------------------------------------------------------
# line edits (real tracked changes)
# ---------------------------------------------------------------------------

def _fix_punctuation(text: str) -> str:
    fixed = re.sub(r"[ \t]+([,;:.!?])", r"\1", text)
    fixed = re.sub(r"\.{2,}", ".", fixed)
    fixed = re.sub(r"\)\s+\.", ").", fixed)
    fixed = re.sub(r"([,;:])(?=[A-Za-z])", r"\1 ", fixed)
    fixed = re.sub(r" {2,}", " ", fixed)
    return fixed


def _title_case(text: str) -> str:
    minor = {"a", "an", "the", "and", "but", "or", "nor", "for", "so", "yet", "at",
             "by", "in", "of", "on", "to", "up", "as", "per", "via", "vs"}
    words = text.split()
    out = []
    for i, word in enumerate(words):
        core = re.sub(r"[^A-Za-z]", "", word)
        if i not in (0, len(words) - 1) and core.lower() in minor:
            out.append(word.lower())
        else:
            out.append(word[:1].upper() + word[1:] if word else word)
    return " ".join(out)


def _fix_agreement(text: str) -> str:
    fixes = [
        (r"\bnor does they\b", "nor do they"),
        (r"\bnor does we\b", "nor do we"),
        (r"\bdoes they\b", "do they"),
        (r"\bis they\b", "are they"),
        (r"\bhas they\b", "have they"),
        (r"\b(\w+)\s+and\s+(\w+)\s+helps\b", r"\1 and \2 help"),
        (r"\b(\w+)\s+and\s+(\w+)\s+has\b", r"\1 and \2 have"),
        (r"\b(\w+)\s+and\s+(\w+)\s+shows\b", r"\1 and \2 show"),
        (r"\b(\w+)\s+and\s+(\w+)\s+makes\b", r"\1 and \2 make"),
        (r"\b(\w+)\s+and\s+(\w+)\s+is\b", r"\1 and \2 are"),
    ]
    for pattern, replacement in fixes:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
    return text


def _build_line_edits(model: DocumentModel, result: AnalysisResult,
                      source_text: str, limit: int = 6) -> list[dict]:
    candidates: list[tuple[str, str, str, str]] = []

    for finding in sorted(result.findings, key=lambda f: -f.priority):
        quote = finding.quote
        rule = finding.rule_id

        if rule == "wordiness" and finding.facts.get("phrase"):
            phrase = str(finding.facts["phrase"])
            replacement = {
                "the reason for that is because": "the cause is",
                "due to the fact that": "because",
                "in order to": "to",
                "has the ability to": "can",
                "at this point in time": "now",
                "in the event that": "if",
                "a large number of": "many",
                "for the purpose of": "to",
                "is able to": "can",
            }.get(phrase.lower())
            if replacement:
                candidates.append((phrase, replacement, "Concision",
                                   "Removes a phrase that repeats an idea the sentence already made."))
            continue

        if rule in {"mla_date_numeric", "apa_date_numeric"} and finding.facts.get("date"):
            raw = str(finding.facts["date"])
            rendered = human_date(raw, "apa" if rule.startswith("apa") else "mla")
            if rendered != raw:
                candidates.append((raw, rendered, "Formatting",
                                   "Matches the date convention required by the style guide."))
            continue

        if rule == "mla_title_case":
            fixed = _title_case(quote)
            if fixed != quote:
                candidates.append((quote, fixed, "Formatting",
                                   "Applies title case to the essay title."))
            continue

        if rule in {"subject_verb"}:
            fixed = _fix_agreement(quote)
            if fixed != quote:
                candidates.append((quote, fixed, "Grammar",
                                   "Makes the verb agree with its subject."))
            continue

        if rule in {"typo_cluster", "space_before_punct", "citation_period_space",
                    "double_period", "missing_space_after_punct"}:
            fixed = _fix_punctuation(quote)
            if fixed != quote:
                candidates.append((quote, fixed, "Punctuation",
                                   "Cleans up spacing around punctuation."))
            continue

        if rule == "informal_diction" and finding.facts.get("term"):
            term = str(finding.facts["term"])
            if term.lower() in {"very", "really"}:
                fixed = re.sub(rf"\b{re.escape(term)}\s+", "", quote, flags=re.IGNORECASE)
                if fixed != quote:
                    candidates.append((quote, fixed, "Diction",
                                       "Removes an empty intensifier."))
            continue

    edits: list[dict] = []
    used: list[tuple[int, int]] = []
    for original, replacement, issue, explanation in candidates:
        if len(edits) >= limit:
            break
        if not original or original not in source_text:
            continue
        start = source_text.find(original)
        end = start + len(original)
        if any(start < used_end and used_start < end for used_start, used_end in used):
            continue
        used.append((start, end))
        edits.append({
            "original_text": original,
            "suggested_replacement": replacement,
            "issue_type": issue,
            "explanation": explanation,
        })
    return edits


# ---------------------------------------------------------------------------
# public entry point
# ---------------------------------------------------------------------------

def build_review(model: DocumentModel, result: AnalysisResult, source_text: str, *,
                 mode: str = "academic", institution: str = "",
                 student_name: str = "", reviewer_name: str = "Raunak Banga") -> dict:
    """Return a DeepReviewPayload-shaped dict computed only from findings."""
    review_mode = "admissions" if mode == "admissions" else "academic"
    scores = _score_pillars(result, review_mode)
    total = sum(v["score"] for v in scores.values())
    endnote = compose_endnote(model, result, reviewer_name=reviewer_name,
                              student_name=student_name or None)
    return {
        "overall_score": total,
        "category_scores": scores,
        "executive_summary": _summary(model, result, scores, review_mode),
        "top_action_items": _actions(result),
        "line_edits": _build_line_edits(model, result, source_text),
        "tutor_overview_letter": "\n\n".join(endnote.paragraphs),
        "institution": institution,
    }
