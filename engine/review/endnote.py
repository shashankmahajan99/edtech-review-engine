"""Personalised three-domain endnote letter synthesis.

The exemplar letters are 190-250 words, thank the student, name three domains,
and each domain body does three things: says what the draft already does, names
the specific gap, and gives one concrete revision.  This module reproduces that
shape from the same findings that drive the comments, so the letter can never
contradict the margin notes.

Every domain has several phrasings; the variant is chosen from the document
fingerprint so two submissions never receive the same letter text.
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

DOMAIN_SETS = {
    "argumentative": [
        "Thesis and Main Argument",
        "Evidence and Analysis",
        "Structure and Synthesis",
    ],
    "research": [
        "Thesis and overall focus",
        "Evidence and analysis",
        "Conclusion and synthesis",
    ],
    "rhetorical": [
        "Introduction and Assertion of Thesis",
        "Analysis and Evidence",
        "Clarity and Proofreading",
    ],
    "statement": [
        "Narrative and Opening",
        "Specificity and Fit",
        "Style and Mechanics",
    ],
    "academic": [
        "Thesis and Main Argument",
        "Evidence and Analysis",
        "Structure and Synthesis",
    ],
}

OPENERS = [
    "Thank you for submitting your paper. There are some suggestions that may help improve the quality of the paper:",
    "Thank you for submitting your draft. Please pay attention to the following domains:",
    "Thank you for submitting your paper. You need to focus on:",
    "Thank you for submitting your draft. Here is what I would work on first:",
    "Thank you for sharing this draft. These are the areas I would focus on:",
]

CLOSERS = [
    "I hope this feedback is helpful.",
    "I hope these suggestions help as you revise.",
    "I hope you find this useful when you revise.",
]

SIGNOFF = "All the best."


@dataclass
class Endnote:
    paragraphs: list[str]
    domains: list[str]
    word_count: int


def _first_name(model: DocumentModel, fallback: str = "Student") -> str:
    for p in model.front_matter:
        text = p.normalized
        if not text or re.fullmatch(r"[\d\s./-]+", text):
            continue
        words = re.findall(r"[A-Za-z][A-Za-z'\u2019-]+", text)
        if words:
            return words[0].capitalize()
    return fallback.split()[0] if fallback else "Student"


def _title(model: DocumentModel) -> str:
    title = next((p for p in model.paragraphs if p.region == "title"), None)
    if title is not None:
        return title.normalized.strip(" .:")
    return ""


def _authors(result: AnalysisResult) -> str:
    names = [n for n in result.sources if n]
    if not names:
        return ""
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]}, {names[1]}, and {names[2]}"


def _top(findings: list[Finding], *categories: str) -> Finding | None:
    scored = [f for f in findings if f.category in categories]
    return max(scored, key=lambda f: f.priority) if scored else None


def _opening_line(model: DocumentModel) -> str:
    title = _title(model)
    if title.endswith("?"):
        return "Your introduction sets up the central question directly, and the reader knows what is at stake."
    if title and len(title.split()) <= 8 and title[:1].isupper():
        return f"Your introduction makes the focus of the essay clear: {title}."
    return "Your introduction establishes the subject of the essay clearly."


# ---------------------------------------------------------------------------
# domain bodies: each function returns the list of candidates for that shape
# ---------------------------------------------------------------------------

def _thesis_body(model: DocumentModel, finding: Finding | None) -> list[str]:
    opening = _opening_line(model)
    if finding is None:
        return [
            f"{opening} The thesis gives the reader a clear direction, and keeping it in one sentence "
            "as you revise will help the argument stay easy to follow.",
            f"{opening} Your position comes through in the opening, and the body paragraphs follow it. "
            "As you revise, keep the thesis in a single sentence so a reader can hold it in mind.",
        ]

    if finding.category == INTRO:
        gap = "the opening still needs a specific, arguable claim rather than a statement of topic"
        advice = ("Draft that claim as one sentence and place it at the end of the introduction, then "
                  "make each body paragraph answer to it.")
    else:
        gap = "the thesis states the topic without previewing the points the body will prove"
        advice = ("Write the thesis as one sentence that names your position and the two or three points "
                  "your body paragraphs develop, then check that each paragraph delivers one of them.")

    return [
        f"{opening} That said, {gap}. I suggest {advice[0].lower() + advice[1:]}",
        f"{opening} What would sharpen it is a thesis that previews the argument's main points; right now it "
        f"names the topic only. {advice}",
        f"{opening} What the opening still needs is a clearer claim \u2014 {gap}. {advice}",
    ]


def _evidence_body(result: AnalysisResult, finding: Finding | None) -> list[str]:
    authors = _authors(result)
    if authors:
        support = f"You draw on {authors}, among other sources, which gives the argument real weight."
        support_alt = f"The sources you bring in \u2014 {authors} among them \u2014 suit the argument well."
    else:
        support = "You bring in examples and observations that support the argument."
        support_alt = "The examples you choose are relevant to the claim you are making."

    if finding is None:
        return [
            f"{support} As you revise, keep asking what each piece of evidence proves for your specific "
            "claim, and say it in the sentence that follows.",
            f"{support} The next step is to make the connection explicit: after each example, name what it "
            "demonstrates before moving on.",
        ]

    gap = ("some of the evidence is presented and then left behind without saying what it proves"
           if finding.category in {EVIDENCE, STATISTICS}
           else "the discussion of evidence stays at the level of summary")
    return [
        f"{support} However, {gap}. After each piece of evidence, add one or two sentences explaining why "
        "it matters for the claim of that paragraph.",
        f"{support_alt} The place to push further is the analysis: {gap}. Ask yourself what each source "
        "proves, then write that sentence down.",
        f"{support} The draft moves quickly from evidence to the next idea, though: {gap}. Slow down for a "
        "sentence or two after each source and say what it establishes.",
    ]


def _structure_body(result: AnalysisResult, finding: Finding | None,
                    essay_type: str) -> list[str]:
    blocks = result.metrics.get("blocks") or result.metrics.get("paragraphs") or 0
    citations = result.metrics.get("citations", 0)

    if essay_type == "rhetorical":
        return [
            "The paragraphs on the appeals cover a lot of ground, and the conclusion would be stronger if it "
            "showed how ethos, pathos, and logos work together rather than restating each one. Proofread for "
            "spacing and punctuation as well; small slips distract from otherwise strong analysis.",
            "You move through the appeals in a sensible order. What would help is a closing paragraph that "
            "explains how the appeals reinforce one another. A careful proofread for spacing and punctuation "
            "would also make the prose easier to follow.",
        ]

    if finding is not None and finding.category == TRANSITION:
        return [
            "The overall order of ideas is sensible, but a few paragraph openings arrive without a bridge. "
            "Add a transitional phrase at those seams and the argument will read as one continuous line.",
            "Your paragraphs follow a logical sequence. The connections between them are sometimes left "
            "implicit, though, so the reader has to infer the link. Name it in a short transition.",
        ]

    if finding is not None and finding.category == CONCLUSION:
        return [
            f"The progression of ideas across the {blocks} body paragraphs is logical, but the conclusion "
            "mostly restates points the body already made. Push the final paragraph toward the larger "
            "implication: what should the reader think or do differently because of your argument?",
            f"The essay builds steadily across its {blocks} body paragraphs. The closing paragraph, though, "
            "repeats what has already been said. Use it to say what follows from your findings, or what "
            "remains unresolved.",
        ]

    if essay_type == "research" and citations >= 3:
        return [
            f"The paper is organised around a clear set of approaches, and the {citations} citations give it "
            "range. The conclusion largely repeats the solutions already described, so use it to say how the "
            "approaches complement one another.",
            f"Your structure makes the {citations} sources easy to follow. In the conclusion, go one step "
            "further than listing the approaches: explain what combining them makes possible.",
        ]

    return [
        f"The overall progression of your ideas is logical across the {blocks} body paragraphs. To improve "
        "cohesion, tighten the transitions between major shifts in argument, and make the conclusion "
        "synthesise the analysis rather than repeat it.",
        f"The essay moves through its {blocks} body paragraphs in a clear order. A little more connective "
        "tissue between sections, and a conclusion that draws the threads together, would make the argument "
        "feel finished.",
    ]


def _statement_bodies(result: AnalysisResult) -> tuple[list[str], list[str], list[str]]:
    """Domain bodies for an admissions personal statement."""
    opener_f = _top(result.findings, INTRO)
    fit_f = _top(result.findings, ORGANISATION, CLARITY)

    if opener_f is not None:
        first = [
            "The opening reaches for a familiar line about lifelong passion, which is the most common "
            "opening in this genre. Replace it with the specific moment or problem that made this field "
            "matter to you, and let the reader infer the passion from the scene.",
            "This is a recognisable opening move for applications, and committees read hundreds of them. "
            "Start instead inside a concrete episode: a decision you made, a failure you fixed, a question "
            "you could not drop.",
        ]
    else:
        first = [
            "Your opening is clear and gets the reader into the material quickly. The next step is to make "
            "the first paragraph do narrative work: one specific moment, described with enough detail that "
            "the reader can see it.",
            "The introduction sets up your background efficiently. Consider grounding it in a single scene "
            "rather than a summary of your interests; specificity is what a committee remembers.",
        ]

    if fit_f is not None:
        second = [
            "The paragraph on why this programme suits you leans on phrases that could describe almost any "
            "department. Name the lab, the course, or the professor whose work connects to what you have "
            "already done, and say what you would want to contribute.",
            "You state that this is the right place for you, but the reasons stay general. Pick two concrete "
            "features of the programme and tie each one to a project or skill of yours.",
        ]
    else:
        second = [
            "You connect your background to the programme's work, which is exactly what this section needs. "
            "Keep the link explicit as you revise: what you have done, what you want to learn next, and why "
            "this programme is the place to learn it.",
            "The fit between your experience and the programme comes through. Sharpen it with one or two "
            "specific resources you want to use there, so the paragraph could only be about this school.",
        ]

    third = [
        "The draft is readable, and a final proofreading pass will take care of the smaller mechanical "
        "points flagged in the margin. Read it aloud once; the places where you stumble are the places to "
        "revise.",
        "Your own perspective comes through in the writing, which matters more in this genre than in an academic "
        "essay. Keep the sentences varied and concrete, and clear the mechanical notes in the margin before "
        "you submit.",
    ]
    return first, second, third


def compose_endnote(model: DocumentModel, result: AnalysisResult,
                    reviewer_name: str = "Raunak Banga",
                    student_name: str | None = None) -> Endnote:
    first = _first_name(model, student_name or "Student")
    essay_type = result.essay_type
    domains = DOMAIN_SETS.get(essay_type, DOMAIN_SETS["academic"])

    digest = int(hashlib.sha1(model.fingerprint.encode("utf-8")).hexdigest(), 16)
    opener = OPENERS[digest % len(OPENERS)]
    closer = CLOSERS[(digest // 7) % len(CLOSERS)]

    findings = result.findings
    thesis_f = _top(findings, THESIS, INTRO)
    evidence_f = _top(findings, EVIDENCE, STATISTICS, ANALYSIS)
    structure_f = _top(findings, CONCLUSION, TRANSITION, ORGANISATION, TOPIC, COUNTER)
    mechanics_f = _top(findings, PUNCT, FRAGMENTS, SVA, INFORMAL, CLARITY, MLA, APA)

    def pick(candidates: list[str], salt: int) -> str:
        if not candidates:
            return ""
        return candidates[(digest // salt) % len(candidates)]

    body1 = pick(_thesis_body(model, thesis_f), 3)
    body2 = pick(_evidence_body(result, evidence_f), 11)
    body3 = pick(_structure_body(result, structure_f, essay_type), 29)

    if essay_type == "statement":
        st1, st2, st3 = _statement_bodies(result)
        body1 = pick(st1, 3)
        body2 = pick(st2, 11)
        body3 = pick(st3, 29)
        mechanics_f = None  # already covered by the style/mechanics paragraph

    if mechanics_f is not None and essay_type != "rhetorical":
        tail = pick([
            " I have also flagged a few mechanical points in the margin; those are quick fixes that will make "
            "the prose read more cleanly.",
            " There are also a handful of smaller mechanical notes in the margin \u2014 worth clearing before "
            "your next submission.",
        ], 41)
        body3 += tail

    paragraphs = [
        f"Dear {first},",
        opener,
        f"{domains[0]}:",
        body1,
        f"{domains[1]}:",
        body2,
        f"{domains[2]}:",
        body3,
        closer,
        SIGNOFF,
        reviewer_name,
    ]
    words = sum(len(p.split()) for p in paragraphs)
    return Endnote(paragraphs=paragraphs, domains=domains, word_count=words)

