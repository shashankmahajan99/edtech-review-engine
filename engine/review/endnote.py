"""Closing letters grounded in the comments actually delivered.

The reviewer corpus supplies the letter shape: greeting, named revision areas,
concrete next steps and a signature. Never invent praise or extra revision
areas to fill a template.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from .analysis import (
    ABSTRACT, ANALYSIS, APA, CLARITY, CONCLUSION, COUNTER, EVIDENCE, FRAGMENTS,
    INFORMAL, INTRO, MLA, ORGANISATION, PUNCT, STATISTICS, SVA, THESIS, TOPIC,
    TRANSITION, AnalysisResult,
)
from .docmodel import DocumentModel
from .persona import compose_all
from .selection import SelectedComment, select_comments
from .endnote_moves import PRIORITY_PLANS

SIGNOFF = "All the best."

_GROUPS = [
    ("Thesis and overall focus", {THESIS, INTRO}),
    ("Abstract", {ABSTRACT}),
    ("Evidence and analysis", {EVIDENCE, STATISTICS, ANALYSIS}),
    ("Paragraph focus and connections", {ORGANISATION, TOPIC, TRANSITION}),
    ("Conclusion and implications", {CONCLUSION}),
    ("Considering another perspective", {COUNTER}),
    ("Sentence clarity", {CLARITY, INFORMAL}),
    ("Grammar and punctuation", {PUNCT, FRAGMENTS, SVA}),
    ("Citation and document formatting", {MLA, APA}),
]

_FOLLOW_THROUGH = {
    "Thesis and overall focus": (
        "Use the points you actually develop in the body to guide this revision. "
        "Then read the introduction on its own: does it prepare the reader for those points?"
    ),
    "Abstract": (
        "Revise the abstract after the body so it reflects the completed discussion. "
        "Check that a reader can identify the purpose and main takeaway without reading the introduction."
    ),
    "Evidence and analysis": (
        "Keep the source's findings separate from your interpretation. Explain the connection "
        "to your paragraph's point, and avoid claiming more than the cited evidence supports."
    ),
    "Paragraph focus and connections": (
        "Read the paragraph openings together after making this change. Each should identify "
        "the point that follows and make its relationship to the previous point clear."
    ),
    "Conclusion and implications": (
        "Build the ending from ideas already developed in the body. Explain what readers can "
        "take away from the discussion without introducing a claim that still needs supporting evidence."
    ),
    "Considering another perspective": (
        "Choose an objection relevant to your specific position. Represent it fairly before "
        "explaining how your evidence answers it, or where your claim needs to be qualified."
    ),
    "Sentence clarity": (
        "Keep the intended meaning while revising the wording. Reread the changed sentence "
        "beside the sentences around it to check that references and connections remain clear."
    ),
    "Grammar and punctuation": (
        "Correct the marked example first, then check for the same issue elsewhere. Read the "
        "revised sentence in full so that a local correction does not leave an incomplete thought."
    ),
    "Citation and document formatting": (
        "Apply the same correction wherever the issue recurs. Use the assigned style guide "
        "alongside any course instructions, and check source details against the original publication."
    ),
    "Opening and personal focus": (
        "Choose details from your own experience. Show what happened, what you did, "
        "and why that experience matters to the direction you now want to take."
    ),
    "Programme fit": (
        "Check names and programme details before including them. Explain how each "
        "resource connects to your experience and what you want to study next."
    ),
}

_RANK0_SHORT_LEADS = (
    "Start with this core passage.",
    "Focus here first.",
    "Begin your revision here.",
    "Anchor the first pass here.",
)

_RANK1_SHORT_LEADS = (
    "Turn to this passage next.",
    "Tighten this section next.",
    "Check this move next.",
    "Address this passage second.",
)

_RANK2_QUESTIONS = {
    "Thesis and overall focus": "What central claim anchors your opening?",
    "Opening and personal focus": "What concrete moment anchors this opening?",
    "Abstract": "What main finding does the abstract report?",
    "Evidence and analysis": "What does this source prove here?",
    "Paragraph focus and connections": "How does this paragraph connect backward?",
    "Programme fit": "Which programme resource fits your goal?",
    "Conclusion and implications": "What larger takeaway closes the draft?",
    "Considering another perspective": "Which objection tests your claim best?",
    "Sentence clarity": "What exact term replaces the vague wording?",
    "Grammar and punctuation": "Where does the clause boundary sit?",
    "Citation and document formatting": "Does every entry match the style guide?",
}

_COMPACT_DIRECTIVES = {
    "Thesis and overall focus": (
        "In {location}, revise {quoted} so the sentence states your governing claim and previews the exact sequence of reasons developed across the body paragraphs."
    ),
    "Opening and personal focus": (
        "In {location}, replace {quoted} with a concrete scene from your own experience that shows what you did and why this field matters to you."
    ),
    "Abstract": (
        "In {location}, expand {quoted} so the summary states your research purpose, the main findings from the body, and the final conclusion in miniature."
    ),
    "Evidence and analysis": (
        "After {quoted} in {location}, add a direct explanation showing how that specific source detail establishes the claim of the paragraph before moving on."
    ),
    "Paragraph focus and connections": (
        "At {quoted} in {location}, open with a clear claim in your own words that links the new paragraph to the preceding point before citing evidence."
    ),
    "Programme fit": (
        "Around {quoted} in {location}, name two specific courses, labs, or faculty members and connect each resource directly to work you have already completed."
    ),
    "Conclusion and implications": (
        "From {quoted} in {location}, move past summarizing earlier points and explain what the combined argument means for readers once the body is finished."
    ),
    "Considering another perspective": (
        "Near {quoted} in {location}, state the strongest objection to your position fairly and explain why your cited evidence still holds up against it."
    ),
    "Sentence clarity": (
        "In {location}, rewrite {quoted} using the exact noun, measurement, or cause-and-effect link so readers do not have to guess your intended meaning."
    ),
    "Grammar and punctuation": (
        "At {quoted} in {location}, align the subject, verb, and clause punctuation, then scan the rest of the draft for the same mechanical pattern."
    ),
    "Citation and document formatting": (
        "In {location}, bring {quoted} into line with the required heading, title, and source-entry conventions, then apply that same format across every page."
    ),
}


@dataclass
class Endnote:
    paragraphs: list[str]
    domains: list[str]
    word_count: int
    evidence: list[dict] = field(default_factory=list)


def _first_name(model: DocumentModel, supplied: str | None = None) -> str:
    if supplied and supplied.strip() and supplied.strip().lower() != 'student':
        return supplied.strip().split()[0]
    first = next((p.text.split('\t', 1)[0].strip() for p in model.front_matter if p.normalized), "")
    first = re.split(r'\s+(?:(?:Mr|Mrs|Ms|Dr)\.?|Professor|Instructor)\s+', first, maxsplit=1, flags=re.I)[0]
    if re.fullmatch(r"[A-Za-z]+(?:[-'][A-Za-z]+)?(?: [A-Za-z]+(?:[-'][A-Za-z]+)?){1,3}", first):
        if not re.search(r"\b(?:Professor|Doctor|Instructor|University|College|Course|English)\b", first):
            return first.split()[0].capitalize()
    return "Student"


def _excerpt(text: str, limit: int = 10) -> str:
    """Keep an exact substring, including any spacing error being discussed."""
    words = list(re.finditer(r"\S+", text))
    if len(words) <= limit:
        return text.strip()
    return text[:words[limit - 1].end()].strip() + "…"


def _location(model: DocumentModel, item: SelectedComment) -> str:
    para = item.finding.paragraph
    if para.region == "references":
        return "the reference section"
    if para.region in {"front_matter", "title"}:
        return "the opening details"
    if para.region == "abstract":
        return "the abstract"
    from .analysis import build_blocks
    positions = {p.index: i + 1 for i, block in enumerate(build_blocks(model)) for p in block.paragraphs}
    return f"body paragraph {positions[para.index]}" if para.index in positions else "the marked passage"


def _split_sents(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _build_asymmetric_section(
    rank_idx: int,
    total_domains: int,
    heading: str,
    item: SelectedComment,
    model: DocumentModel,
    quoted: str,
    seed: int,
) -> str:
    """Compose an asymmetric, bursty priority block grounded in finding facts."""
    finding = item.finding
    loc = _location(model, item)
    plan_template = PRIORITY_PLANS.get(finding.rule_id)
    plan_text = plan_template.format(anchor=quoted) if plan_template else ""
    plan_sents = _split_sents(plan_text) if plan_text else []
    follow_sents = _split_sents(_FOLLOW_THROUGH.get(heading, ""))
    compact_long = _COMPACT_DIRECTIVES.get(
        heading,
        "At {quoted} in {location}, revise the passage so the main point and its supporting details work together clearly across the paragraph.",
    ).format(quoted=quoted, location=loc)

    fact_detail = ""
    if finding.facts.get("source"):
        fact_detail = f" — specifically the {finding.facts['source']} material —"
    elif finding.facts.get("term"):
        fact_detail = f" — particularly the term “{finding.facts['term']}” —"
    elif finding.facts.get("suggested"):
        fact_detail = f" — using {finding.facts['suggested']} —"
    else:
        fact_detail = f" — in {loc} —"

    if total_domains < 3:
        # When only 1 or 2 domains fire, use fuller plans so the letter stays >= 138 words
        short_lead = _RANK0_SHORT_LEADS[(seed + rank_idx) % len(_RANK0_SHORT_LEADS)]
        if plan_text:
            base = f"{short_lead} {plan_text}"
            if total_domains == 1 and follow_sents:
                base += " " + " ".join(follow_sents)
            return base
        return f"{short_lead} {compact_long} " + " ".join(follow_sents)

    if rank_idx == 0:
        # Priority 1: ~50-65 words, direct quote + em-dash interruption + short (<=8w) & long (>=22w) sentences
        short_lead = _RANK0_SHORT_LEADS[seed % len(_RANK0_SHORT_LEADS)]
        if plan_sents:
            first_plan = plan_sents[0]
            if "—" not in first_plan and len(first_plan.split()) < 22:
                long_clause = (
                    f"{first_plan.rstrip('.')} {fact_detail} so the reader can trace how each supporting reason connects back to your central argument."
                )
            elif "—" not in first_plan:
                long_clause = re.sub(
                    r",\s+",
                    f"{fact_detail} ",
                    first_plan,
                    count=1,
                )
            else:
                long_clause = first_plan
            tail = " ".join(plan_sents[1:3]) if len(plan_sents) > 1 else (follow_sents[0] if follow_sents else "")
            section = f"{short_lead} {long_clause} {tail}".strip()
        else:
            long_clause = re.sub(r",\s+", f"{fact_detail} ", compact_long, count=1)
            tail = follow_sents[0] if follow_sents else ""
            section = f"{short_lead} {long_clause} {tail}".strip()
        return section

    if rank_idx == 1:
        # Priority 2: ~25-35 words, punchy and direct (short <=8w sentence + long >=22w sentence)
        short_lead = _RANK1_SHORT_LEADS[(seed + 1) % len(_RANK1_SHORT_LEADS)]
        return f"{short_lead} {compact_long}"

    # Priority 3 (rank_idx == 2): ~40-55 words, opening with a diagnostic question (<=8w) + long (>=22w) sentence
    question = _RANK2_QUESTIONS.get(heading, "How does this passage advance your point?")
    if plan_sents and len(plan_sents) >= 2:
        # Pick the anchored sentence and one concrete follow-up sentence, ensuring >=22w long sentence
        s_anchor = plan_sents[0]
        if len(s_anchor.split()) < 22:
            s_anchor = (
                f"{s_anchor.rstrip('.')}, making sure the revised wording in {loc} connects directly to the point your paragraph sets out to establish."
            )
        s_next = plan_sents[-1]
        return f"{question} {s_anchor} {s_next}"

    tail = follow_sents[-1] if follow_sents else "Apply that check across the remaining paragraphs."
    return f"{question} {compact_long} {tail}"


def compose_endnote(model: DocumentModel, result: AnalysisResult,
                    reviewer_name: str = "Raunak Banga",
                    student_name: str | None = None,
                    composed: list[tuple[SelectedComment, str]] | None = None) -> Endnote:
    if composed is None:
        composed = compose_all(model, select_comments(model, result), result.essay_type)

    groups: dict[str, list[tuple[SelectedComment, str]]] = {}
    for item, body in composed:
        categories = set(item.category.split(" AND "))
        heading = next((name for name, members in _GROUPS if categories & members), None)
        if heading:
            if result.essay_type == "statement" and heading == "Thesis and overall focus":
                heading = "Opening and personal focus"
            elif result.essay_type == "statement" and item.finding.rule_id == "statement_no_specific_fit":
                heading = "Programme fit"
            groups.setdefault(heading, []).append((item, body))

    focus_order = {'Thesis and overall focus': 0, 'Opening and personal focus': 0,
                   'Evidence and analysis': 1, 'Paragraph focus and connections': 2,
                   'Programme fit': 2, 'Conclusion and implications': 3,
                   'Abstract': 3, 'Considering another perspective': 4,
                   'Sentence clarity': 5, 'Grammar and punctuation': 6,
                   'Citation and document formatting': 7}
    ranked = sorted(groups, key=lambda name: (focus_order.get(name, 8),
                    -max(i.finding.priority for i, _ in groups[name])))[:3]
    title = next((p.normalized for p in model.paragraphs if p.region == "title"), "")
    opening = f"Thank you for sharing your draft, “{title}”." if title else "Thank you for sharing your draft."
    paragraphs = [f"Dear {_first_name(model, student_name)},", opening]
    evidence: list[dict] = []

    base_seed = int(hashlib.sha1((model.fingerprint or "").encode("utf-8")).hexdigest()[:8], 16)

    for rank_idx, heading in enumerate(ranked):
        item, _body = max(groups[heading], key=lambda pair: pair[0].finding.priority)
        finding = item.finding
        excerpt = _excerpt(finding.quote)
        quoted = f'‘{excerpt}’' if re.search('[“”"]', excerpt) else f'“{excerpt}”'
        section = _build_asymmetric_section(
            rank_idx=rank_idx,
            total_domains=len(ranked),
            heading=heading,
            item=item,
            model=model,
            quoted=quoted,
            seed=base_seed + rank_idx,
        )
        paragraphs.extend([heading + ":", section])
        evidence.append({"domain": heading, "rule": finding.rule_id,
                         "paragraph": finding.paragraph.index, "quote": finding.quote})

    if ranked:
        paragraphs.append('Please use the margin notes to locate the passages while revising.')
    else:
        paragraphs.append("No revision areas were selected for this letter. Please review the draft with your assignment instructions.")
    paragraphs.extend([SIGNOFF, reviewer_name])

    # Ensure 1- or 2-domain letters meet the 138-word reference floor
    total_words = sum(len(p.split()) for p in paragraphs)
    if ranked and total_words < 138:
        first_section_idx = next((i for i, p in enumerate(paragraphs) if p.endswith(":")), None)
        if first_section_idx is not None and first_section_idx + 1 < len(paragraphs):
            extra = _FOLLOW_THROUGH.get(ranked[0], "")
            if extra and extra not in paragraphs[first_section_idx + 1]:
                paragraphs[first_section_idx + 1] += " " + extra
            total_words = sum(len(p.split()) for p in paragraphs)
        if total_words < 138:
            paragraphs[-3] = (
                "Please use the margin notes to locate each marked passage while revising, "
                "and reread the updated paragraphs together so the argument, evidence, and formatting stay consistent from start to finish."
            )

    from .anti_ai_patterns import scrub_ai_tells
    cleaned_paragraphs = []
    for i, p in enumerate(paragraphs):
        if p.startswith("Dear ") or p.endswith(":") or p in {SIGNOFF, reviewer_name}:
            cleaned_paragraphs.append(p)
        else:
            cleaned_paragraphs.append(scrub_ai_tells(p, seed=base_seed + i))
    paragraphs = cleaned_paragraphs

    return Endnote(paragraphs, ranked, sum(len(p.split()) for p in paragraphs), evidence)
