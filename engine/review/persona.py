"""Deterministic comment composition in a human reviewer persona.

Each rule owns several phrasings mined from the reviewer's real deliverables: a
diagnosis that names what is happening in the sentence, then one concrete
directive, occasionally closing with a Socratic question.  Variants deliberately
differ in length (short command, two-sentence note, longer reasoned paragraph)
because uniform sentence length is the clearest machine-written tell.

The variant is chosen by hashing the document fingerprint with the finding's
position, so the same document always produces byte-identical comments
(reproducible) and different documents almost never share phrasing.

Nothing here calls a model.  Composition is pure string work.
"""
from __future__ import annotations

import hashlib
import re
from typing import Any

from .selection import SelectedComment
from .docmodel import DocumentModel

# Words that make a comment read machine-written.  Mirrors the banned list in
# engine/anti_ai_humanizer.py but is enforced here at composition time.
BANNED_PHRASES = (
    "delve", "delving", "testament to", "tapestry", "beacon of", "paramount",
    "multifaceted", "commendable", "furthermore", "moreover", "in conclusion",
    "crucial role", "pivotal", "fostering", "fosters", "embarking", "vibrant",
    "interplay", "realm", "holistic", "it is important to note",
    "it is worth noting", "sheds light on", "serves as a", "intricate",
    "dynamic interplay", "underscores the importance", "unwavering",
    "profound impact", "inextricably", "navigating the complexities",
    "in today's fast-paced", "as an ai", "dive into", "unpack",
)

_MONTHS = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May", 6: "June",
    7: "July", 8: "August", 9: "September", 10: "October", 11: "November",
    12: "December",
}


def human_date(numeric: str, style: str) -> str:
    """Render 9/27/2026 or 9-22-26 the way the target style expects."""
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", numeric.strip())
    if not m:
        return numeric
    month, day, year = int(m.group(1)), int(m.group(2)), m.group(3)
    if len(year) == 2:
        year = f"20{year}"
    month_name = _MONTHS.get(month, "")
    if not month_name:
        return numeric
    if style == "apa":
        return f"{month_name} {day}, {year}"
    return f"{day} {month_name} {year}"


def _quote_list(items: list[str], limit: int = 3) -> str:
    cleaned = [i.strip() for i in items if i and i.strip()][:limit]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return f"\u201c{cleaned[0]}\u201d"
    if len(cleaned) == 2:
        return f"\u201c{cleaned[0]}\u201d and \u201c{cleaned[1]}\u201d"
    return ", ".join(f"\u201c{c}\u201d" for c in cleaned[:-1]) + f", and \u201c{cleaned[-1]}\u201d"


# ---------------------------------------------------------------------------
# Template library: (diagnosis, directive) pairs.  {slots} come from findings.
# ---------------------------------------------------------------------------

TEMPLATES: dict[str, list[tuple[str, str]]] = {
    # -- formatting ---------------------------------------------------------
    "mla_date_numeric": [
        ("The date is the first thing a reader checks in an MLA heading, and the numeric form here "
         "does not match the convention.",
         "Write it out as {suggested}, without slashes or hyphens."),
        ("Dates in MLA run day-month-year.", "Set this one as {suggested}."),
        ("A numeric date like {date} reads as a draft artifact in an MLA heading.",
         "Spell it out as {suggested} and keep the month capitalized."),
    ],
    "apa_date_numeric": [
        ("The date on an APA title page should be written in words, not numerals.",
         "Change {date} to {suggested}."),
        ("Use {suggested} rather than {date}.", ""),
        ("Title pages spell out the month, and the numbers here look copied straight from a calendar.",
         "Rewrite the line as {suggested}."),
    ],
    "mla_heading_order": [
        ("In standard MLA format, the heading follows a fixed order: student name, instructor name, "
         "course name and number, and date.",
         "Reorder these four lines so the date sits last."),
        ("The heading lines are out of sequence.",
         "MLA runs name, instructor, course, then date, so the date belongs at the bottom."),
        ("Move the date below the course line; an MLA heading ends with the date.", ""),
    ],
    "mla_header_missing": [
        ("Ensure you have a right-aligned header in the top-right margin of every page featuring "
         "your last name and page number.", ""),
        ("There is no running header with your surname and page number, which MLA expects on every page.",
         "Add one, right-aligned in the top margin."),
        ("Add the standard last-name-and-page header, right-aligned, on each page.", ""),
    ],
    "mla_title_case": [
        ("Title case capitalizes the first word, the last word, and every major word in between, "
         "while articles and short prepositions stay lowercase.",
         "Bring this title in line with that pattern."),
        ("This title is not in title case.",
         "Capitalize the major words and leave the short connecting words lowercase."),
        ("Adjust the capitalization here to title case.", ""),
    ],
    "title_period": [
        ("Titles do not take a period.", "Remove it."),
        ("The period after the title is unnecessary; drop it so the title stands on its own.", ""),
    ],
    "apa_instructor_missing": [
        ("Student title pages carry four lines: title, author, affiliation, and instructor.",
         "Add the instructor's name below the course so the block is complete."),
        ("The title page lists your name and course but not your instructor.",
         "Insert that line under the course."),
        ("Add the instructor's name beneath the course line.", ""),
    ],
    "apa_course_name": [
        ("It helps to include the full course name alongside the code, since a reader outside the "
         "institution will not know what the number covers.", "Write the course name out."),
        ("The heading gives only a course code.", "Add the full course title next to it."),
        ("Spell out the course name beside the code.", ""),
    ],
    "mla_raw_url_container": [
        ("In MLA citation style, container names should be formatted as formal titles rather than "
         "raw web addresses with mixed capitalization.",
         "Replace the address with the site's title in italics."),
        ("A raw web address is standing in for the container title here.",
         "Use the publication or site name instead, and italicize it."),
        ("Use the site's title in italics, not its URL.", ""),
    ],
    "mla_container_italics": [
        ("Make sure the container or journal names are set in italics.",
         "Only the article title belongs in quotation marks."),
        ("The container title here is not italicized.",
         "Italicize the journal name so it reads as a container."),
        ("Italicize the journal name; the article title stays in quotes.", ""),
    ],
    "apa_database": [
        ("Database names and indexing services are omitted when a standard DOI link is provided.",
         "Delete the database name."),
        ("Naming the database duplicates information the DOI already carries, so APA drops it.",
         "Remove it from the entry."),
        ("Drop the database name; the DOI is enough.", ""),
    ],
    "org_name_mismatch": [
        ("Your text cites {long}, but the References list uses {short}.",
         "Use one form consistently, then group the entries chronologically."),
        ("The in-text citation and the reference entry use different forms of the same organization.",
         "Pick {long} or {short} and apply it in both places."),
        ("Match the in-text name to the reference entry.", ""),
    ],
    "works_cited_top_margin": [
        ("Do not leave extra lines before this section.", "Start it from the very top of the page."),
        ("The Works Cited heading is pushed down by blank space.",
         "Remove the extra spacing so it begins at the top margin."),
    ],
    "implausible_year": [
        ("This looks like a placeholder rather than the real publication year.",
         "Replace it with the actual date for the source."),
        ("The year here does not match the source's publication date.",
         "Check the original and correct it."),
    ],

    # -- abstract -----------------------------------------------------------
    "abstract_intro": [
        ("This reads like an introduction, not an abstract.", ""),
        ("Your abstract seems more like the introduction.",
         "An abstract should give a quick snapshot of the paper's purpose, major ideas, and conclusion."),
        ("This abstract sets up the topic but never states what the paper actually concludes.",
         "Add the findings or the main takeaway so a reader can skim it."),
        ("An abstract summarizes the whole paper in miniature: purpose, method, findings, conclusion.",
         "This one stops at the setup, so fold in the central argument and what it establishes."),
    ],

    # -- thesis ---------------------------------------------------------------
    "thesis_vague": [
        ("Your thesis reads a bit general.",
         "Make it more specific by showing how the main ideas connect to each other."),
        ("The thesis names the subject but leaves the actual claim open.",
         "State the point you want the reader to take away, then let the body prove it."),
        ("The thesis keeps its distance from an actual claim.",
         "Replace the general language with the assertion your body paragraphs actually make."),
        ("What point do you want to make about how these ideas fit together?",
         "Answer that in the thesis, in one sentence."),
    ],
    "thesis_no_preview": [
        ("Your thesis outlines your broad topic, but could be tighter.",
         "Make sure your thesis explicitly previews the major analytical points your body paragraphs "
         "will explore."),
        ("The thesis states a position but does not show the road ahead.",
         "Name the two or three points your body paragraphs will prove, in the order they appear."),
        ("Add a short preview of the points the body will prove.", ""),
        ("Right now the thesis tells me what the essay is about, not what it will prove.",
         "A reader should be able to finish the introduction and know the sequence of claims coming. "
         "Name the two or three points the body will make, in the order they appear, and check that "
         "each paragraph delivers one of them."),
    ],
    "thesis_rhetorical_missing": [
        ("The introduction describes the text and its purpose but never states the rhetorical thesis.",
         "After introducing the piece, clarify which rhetorical appeals the analysis will examine and "
         "how they work together."),
        ("A rhetorical analysis needs a thesis that names the appeals being analyzed.",
         "Add a sentence identifying which of ethos, pathos, and logos the body paragraphs will trace."),
        ("The thesis here summarizes the article instead of promising an analysis of it.",
         "Commit to a claim about how the appeals operate and why they persuade."),
    ],
    "thesis_missing": [
        ("The introduction does not yet contain a thesis that states your position.",
         "Add one sentence that names your argument and the points that support it."),
        ("It is hard to find the essay's central claim in this opening.",
         "State it directly, ideally at the end of the introduction."),
    ],
    "thesis_spread": [
        ("The thesis is spread across several sentences, which makes it ambiguous.",
         "Compress it into one sentence that states your opinion clearly."),
        ("Two separate claims here are doing the work of one thesis.",
         "Combine them into a single sentence so the argument has a center."),
    ],
    "intro_generic": [
        ("The opening is too general to engage readers.",
         "What concrete moment or observation first drew you to this topic, and how can it open the essay?"),
        ("A broad statement like this could start almost any essay.",
         "Open with the specific case, statistic, or scene that made the question matter."),
    ],

    # -- body ----------------------------------------------------------------
    "transition_abrupt": [
        ("The shift in focus here feels a little sudden.",
         "Try adding a transitional phrase to bridge the previous point and this new idea."),
        ("This paragraph opens a new line of thought without signalling the move.",
         "Add a sentence or phrase that carries the reader across."),
        ("The connection between the last paragraph and this one is left implicit.",
         "Make it explicit with a transition at the start."),
    ],
    "evidence_no_analysis": [
        ("The paragraph presents valuable evidence, but the analysis is too summarizing.",
         "Once you present these findings, elaborate on what the data proves and how it supports the "
         "main claim."),
        ("The evidence arrives and the paragraph moves on before explaining it.",
         "Add a sentence or two on what this {source} result means for your argument."),
        ("This citation is doing the work of an argument by itself.",
         "Spell out what the reader should conclude from it."),
        ("The evidence is strong, but the paragraph never says why it matters.",
         "Connect the finding back to the claim of the paragraph."),
        ("The paragraph summarizes what the study found and then moves on.",
         "That is the point where the analysis has to start: say what the finding means for your "
         "claim, why it matters, and how it changes the reader's understanding. A sentence or two "
         "is enough, but without it the source is only being reported."),
    ],
    "statistics_no_analysis": [
        ("The statistic is vivid, but the paragraph does not explain what it demonstrates.",
         "Say what the number proves before moving on."),
        ("A figure like {stat} carries weight only when the analysis interprets it.",
         "Add the sentence that tells the reader what it shows."),
    ],
    "study_listing": [
        ("The paragraph summarizes several studies but does not help readers see the connections "
         "among them.", "Compare the findings to reveal the main idea they support."),
        ("Several sources are listed side by side here.",
         "Say how {sources} relate to one another, not just what each one found."),
        ("This reads as a list of studies rather than a synthesis.",
         "Group the findings by what they agree on, then note any tension."),
    ],
    "statement_cliche_opener": [
        ("This is one of the most common openings in personal statements, and a committee reads hundreds "
         "of them each cycle.",
         "Open instead with the specific moment, problem, or decision that made this field matter to you."),
        ("A sentence like this could begin almost any statement in this applicant pool.",
         "Trade the general claim for a concrete scene the reader can see."),
    ],
    "statement_generic_claim": [
        ("\u201c{phrase}\u201d could describe almost any programme, so it does little work here.",
         "{hint}."),
        ("The phrase \u201c{phrase}\u201d is a placeholder rather than a reason.",
         "{hint}."),
    ],
    "statement_no_specific_fit": [
        ("Nothing in the draft names a specific course, lab, or professor, which is the part committees "
         "look for in the fit paragraph.",
         "Name two concrete resources and connect each one to something you have already done."),
        ("The statement argues that you are a strong candidate but not why this programme in particular.",
         "Add the specific names and resources that make the match real."),
    ],
    "conclusion_announced": [
        ("\u201cIn conclusion\u201d announces the ending rather than earning it.",
         "Cut the phrase and let the final paragraph close on the idea itself."),
        ("Signposting the conclusion is unnecessary in an essay this short.",
         "Remove the marker and end on the substance."),
    ],
    "para_unsupported": [
        ("This paragraph makes its case without a source, while the rest of the draft is evidenced.",
         "Add the study, statistic, or quotation that supports the claim."),
        ("The claim here is asserted rather than shown.",
         "Bring in one source that would let a sceptical reader accept it."),
    ],
    "para_drift": [
        ("The paragraph opens on one claim and closes somewhere else.",
         "Return to the opening claim in the final sentence so the paragraph reads as one unit."),
        ("The idea announced in the first sentence is not picked up again by the end.",
         "Close the loop before moving to the next paragraph."),
    ],
    "para_filler": [
        ("\u201c{term}\u201d appears {count} times in this paragraph.",
         "Replace the repetition with the specific detail each sentence needs."),
        ("The paragraph leans on \u201c{term}\u201d {count} times.",
         "Cut the filler and let the nouns and verbs carry the meaning."),
    ],
    "para_monotone": [
        ("Every sentence in this paragraph runs about {mean} words.",
         "Put one short sentence beside a longer one so the important point lands."),
        ("The sentences here are metronomic in length.",
         "Vary the rhythm: a brief statement after a long one reads as emphasis."),
    ],
    "para_passive": [
        ("There are {count} passive constructions in this paragraph.",
         "Name the actor and use an active verb where the actor matters."),
        ("The paragraph hides its actors behind passive verbs.",
         "Convert at least one of them so the sentence says who does what."),
    ],
    "para_no_claim": [
        ("The paragraph opens with a fact rather than a claim.",
         "State the point the fact is meant to support, then present it."),
        ("The first sentence reports rather than argues.",
         "Turn it into a topic sentence that tells the reader what to conclude."),
    ],
    "conclusion_summary": [
        ("The conclusion restates points that already appear in the body.",
         "What is the larger implication for readers, and how can you end on that instead?"),
        ("This closes the loop but adds nothing new.",
         "Push the final reflection toward why the argument matters beyond the page."),
        ("The conclusion reiterates several important points from the essay, though most of them have "
         "already been made in the body.", "What is the larger implication for the reader?"),
        ("The final paragraph gathers the main points again, but it does not tell me what to do "
         "with them.",
         "Try ending on the implication instead: what should the reader now believe, or what follows "
         "from your argument beyond this assignment? That is the sentence the conclusion is missing."),
    ],
    "conclusion_thin": [
        ("The conclusion is brief and mostly restates the main points.",
         "Show how the points connect, then explain what the connection reveals."),
        ("This closing paragraph lists ideas without tying them together.",
         "Draw the threads into one statement about the essay's overall significance."),
    ],
    "conclusion_and_fragments": [
        ("The conclusion reviews the techniques but does not connect them, and several sentences are "
         "fragments rather than complete statements.",
         "Tie the observations together, then check that each sentence has a subject, a verb, and a "
         "complete idea."),
        ("This closing paragraph lists points without showing how they relate, and a few of the "
         "sentences are incomplete.",
         "Draw the threads together in full sentences so the ending lands as one thought."),
    ],
    "conclusion_and_punctuation": [
        ("The conclusion restates earlier points and needs a proofread for spacing and punctuation.",
         "Tie the points together and clean up the marks before submitting."),
    ],
    "thesis_and_grammar": [
        ("The thesis needs a sharper claim, and the sentence also has an agreement problem.",
         "Fix the agreement first, then tighten the claim so it previews your main points."),
    ],
    "counterargument_missing": [
        ("The argument never addresses the strongest objection to its claim.",
         "Add a paragraph that fairly states the opposing view, then answers it."),
        ("A persuasive essay gains credibility by meeting the counterargument head on.",
         "Acknowledge the best objection and explain why your position still holds."),
    ],
    "vague_pronoun": [
        ("This sentence opens with a pronoun whose referent is not obvious.",
         "Name the thing you mean so the sentence stands on its own."),
        ("\u201cThis\u201d points backward without saying what it refers to.",
         "Replace it with the specific noun."),
    ],
    "informal_diction": [
        ("The word \u201c{term}\u201d is a bit vague for academic writing.",
         "What specific evidence can show the size of the change?"),
        ("\u201c{term}\u201d reads as conversational rather than analytical.",
         "Swap in the precise measurement or description."),
        ("This phrasing is informal for an academic essay.",
         "Choose a more exact term, or replace it with the evidence itself."),
    ],
    "wordiness": [
        ("The sentence is a bit wordy because \u201c{phrase}\u201d repeats the same idea.",
         "Identify the cause-and-effect relationship and remove unnecessary words."),
        ("\u201c{phrase}\u201d can be said in fewer words.",
         "Tighten the sentence so the point lands faster."),
        ("This phrase delays the actual claim.", "Trim it to the shorter equivalent."),
    ],
    "comma_splice": [
        ("Two independent clauses are joined by a comma here.",
         "Use a semicolon, a period, or a subordinating conjunction instead."),
        ("The comma before this connector is doing work a period should do.",
         "Split the sentence or make one clause dependent."),
    ],
    "topic_evidence_opener": [
        ("The paragraph opens with evidence rather than a claim.",
         "Start with a topic sentence that says what the paragraph will prove, then bring in the source."),
        ("A citation in the first sentence leaves the reader without a topic sentence.",
         "Lead with your point, and let the evidence follow it."),
        ("This paragraph begins in the middle of the evidence.",
         "Open with a sentence that names the idea the evidence supports."),
        ("The paragraph begins with a source instead of a claim.",
         "Put the claim first, in your own words, and then let the evidence support it. As written, "
         "the reader meets the citation before knowing what it is meant to prove, which makes the "
         "paragraph feel like a list rather than an argument."),
    ],
    "repeated_opener": [
        ("Several paragraphs open with the same \u201c{opener}\u201d construction.",
         "Vary the openings so each one announces its own point."),
        ("The paragraph openings follow an identical pattern.",
         "Rework this one so the transition grows out of the previous idea."),
    ],
    "paragraph_overlong": [
        ("Two ideas are competing for the same paragraph here.",
         "Split it where the subject changes, and give each half its own topic sentence."),
        ("This paragraph is doing two jobs.", ""),
        ("This paragraph changes direction without giving the reader a break.",
         "Cut it at the shift and open the next paragraph with the new claim."),
        ("This paragraph is carrying two jobs at once.",
         "Find the sentence where the subject changes, split there, and give the new paragraph its "
         "own topic sentence. Both halves will read faster, and the second idea will stop feeling "
         "like an afterthought."),
    ],
    "mla_heading_same_line": [
        ("Each item in an MLA heading belongs on its own line.",
         "Put the instructor's name on the line below yours."),
        ("Two heading elements are typed on one line here.",
         "Separate them so name, instructor, course, and date each get a line."),
    ],
    "quote_no_page": [
        ("A direct quotation needs a page reference in MLA.",
         "Add the page number in parentheses after the quotation."),
        ("This quotation is not tied to a location in the source.",
         "Add the page number so the reader can find the passage."),
    ],

    # -- mechanics -------------------------------------------------------------
    "subject_verb": [
        ("The subject and verb do not agree here, which makes the sentence sound awkward.",
         "Identify whether the subject is singular or plural, then match the verb to it."),
        ("The verb form does not match its subject.",
         "Reread the sentence, find the subject, and adjust the verb."),
        ("The sentence contains a grammatical agreement issue that affects clarity.",
         "Reread it and identify the subject of the verb, then check whether the verb form matches "
         "that subject."),
    ],
    "space_before_punct": [
        ("A space appears before the punctuation here.",
         "Remove the gap so the mark sits flush against the word."),
        ("Close the gap before the punctuation.", ""),
    ],
    "citation_period_space": [
        ("Review where the period should appear when a sentence ends with a parenthetical citation, and "
         "check whether an unnecessary space appears before the punctuation.", ""),
        ("The period is separated from the citation by a space.",
         "Place it immediately after the closing parenthesis."),
    ],
    "double_period": [
        ("There is a doubled period here.", "Reduce it to a single mark."),
        ("This sentence ends twice; delete the stray period.", ""),
    ],
    "missing_space_after_punct": [
        ("A space is missing after this punctuation mark.",
         "Add one so the words do not run together."),
    ],
    "typo_cluster": [
        ("The paper has a number of typos and formatting problems that hinder readability.",
         "Read once more for spacing and punctuation \u2014 for example: {examples}."),
        ("Small formatting slips recur through the draft.",
         "A careful proofread would catch cases like {examples}."),
        ("Spacing and punctuation problems appear often enough to distract a reader from the argument.",
         "Typical examples include {examples}."),
    ],
    "typo_spacing": [
        ("Stray extra spaces run through the draft and break the reading rhythm.",
         "A single careful pass for spacing will clean most of them up."),
        ("The spacing is inconsistent across the document.",
         "One proofreading pass for double spaces and stray gaps will settle it."),
    ],
    "fragment": [
        ("This is a fragment rather than a complete sentence.",
         "Check that it has a subject, a verb, and a complete idea."),
        ("The sentence is missing its main clause.",
         "Attach it to the sentence it depends on, or give it a subject and verb."),
    ],
}


_QUESTIONS = [
    "What would that look like here?",
    "Which sentence would you start with?",
    "How would you phrase that in one line?",
]

EXTRAS: dict[str, list[str]] = {    "THESIS STATEMENT": [
        "Point to the sentence that says what you will prove, then make sure the body answers it.",
        "Read the introduction on its own and ask what a reader now expects you to argue.",
    ],
    "INTRODUCTION": [
        "The first sentence has to earn the second one.",
        "A concrete opening detail will do more work than a general claim.",
    ],
    "ANALYSIS OF EVIDENCE": [
        "Add the sentence that tells me what the evidence proves.",
        "Right now the source speaks and you do not. Put your reading of it on the page.",
    ],
    "STATISTICS": [
        "Tell me what the number means, not just what it is.",
        "Follow the figure with the conclusion you want me to draw from it.",
    ],
    "CONCLUSION": [
        "End on the implication, not the recap.",
        "Say why the argument matters beyond this assignment.",
    ],
    "TRANSITION": [
        "One sentence linking the two ideas is enough.",
        "Name the connection explicitly instead of letting the reader infer it.",
    ],
    "TOPIC SENTENCE": [
        "Tell me the paragraph's job in its first sentence.",
        "Put the claim first, then the evidence that supports it.",
    ],
    "ORGANISATION": [
        "Put the two ideas in the order you want me to think about them.",
        "Say why this point comes before the next one.",
    ],
    "PUNCTUATION": [
        "These are quick fixes once the ideas are settled.",
        "Fix it here and check the rest of the paragraph for the same slip.",
    ],
    "SUBJECT-VERB AGREEMENT": [
        "Find the subject first, then make the verb agree with it.",
        "Read the sentence aloud; the mismatch is easier to hear than to see.",
    ],
    "INFORMAL WRITING": [
        "Name the specific effect rather than the general impression.",
        "The more precise word is usually the shorter one.",
    ],
    "SENTENCE CLARITY": [
        "The simpler version is also the more confident one.",
        "Say it once, in order, without making me backtrack.",
    ],
    "FRAGMENTS": [
        "Read the sentence alone; the missing piece is easier to spot.",
        "Give it a subject and a verb, or attach it to the sentence it depends on.",
    ],
    "ABSTRACT": [
        "After the abstract, I should know what you found, not just what you studied.",
        "The abstract is a miniature of the paper, not a preview of the introduction.",
    ],
}


def _clean(text: str) -> str:
    """Normalise spacing *outside* quoted material.

    Quoted specimens are evidence: a double space or a space before a comma
    inside them is the defect being described, so it must survive.
    """
    quoted = re.findall(r"\u201c[^\u201d]*\u201d", text)
    placeholders: dict[str, str] = {}
    for i, segment in enumerate(quoted):
        key = f"\x00{i}\x00"
        placeholders[key] = segment
        text = text.replace(segment, key, 1)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    for key, segment in placeholders.items():
        text = text.replace(key, segment)
    text = text.strip()
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


class CommentComposer:
    """Compose comment bodies for selected findings."""

    def __init__(self, model: DocumentModel, essay_type: str = "academic"):
        self.model = model
        self.essay_type = essay_type
        self._used_openers: set[str] = set()
        self._used_phrasings: set[str] = set()
        self._used_skeletons: set[str] = set()
        self._lengths: list[int] = []

    def _facts(self, finding) -> dict[str, Any]:
        facts = dict(finding.facts)
        if facts.get("stat"):
            facts.setdefault("source", finding.facts.get("source") or facts["stat"])
        if facts.get("sources"):
            facts["sources"] = _quote_list([str(s) for s in facts["sources"]], 2)
        if facts.get("examples"):
            facts["examples"] = _quote_list([str(s) for s in facts["examples"]], 4)
        if facts.get("vague"):
            words = [str(w) for w in facts["vague"]]
            facts["vague"] = " and ".join(f"\u201c{w}\u201d" for w in words[:2])
        if facts.get("date"):
            facts["suggested"] = human_date(str(facts["date"]), self.model.style)
        if facts.get("source"):
            src = facts["source"]
            if isinstance(src, list):
                src = src[0] if src else ""
            facts["source"] = str(src).strip().rstrip(",")
        facts.setdefault("term", "")
        facts.setdefault("phrase", "")
        facts.setdefault("long", "World Health Organization")
        facts.setdefault("short", "WHO")
        facts.setdefault("opener", "")
        facts.setdefault("stat", "")
        facts.setdefault("sources", "")
        facts.setdefault("examples", "")
        facts.setdefault("vague", "")
        facts.setdefault("date", "")
        facts.setdefault("suggested", "")
        if facts.get("hint"):
            hint = str(facts["hint"]).strip()
            facts["hint"] = hint[0].upper() + hint[1:] if hint else hint
        else:
            facts.setdefault("hint", "")
        return facts

    def _variant_key(self, finding) -> str:
        raw = f"{self.model.fingerprint}|{finding.rule_id}|{finding.paragraph.index}|{finding.start}"
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()

    def compose(self, selected: SelectedComment) -> str:
        finding = selected.finding
        rule = finding.rule_id
        candidates = TEMPLATES.get(rule)
        if rule == "evidence_no_analysis" and finding.category == "STATISTICS":
            candidates = TEMPLATES.get("statistics_no_analysis", candidates)
        if rule == "typo_cluster" and not finding.facts.get("examples"):
            candidates = TEMPLATES.get("typo_spacing", candidates)
        if not candidates:
            candidates = [
                ("This part of the draft needs another look.",
                 "Revise it so the idea is clear and fully supported."),
            ]

        digest = int(self._variant_key(finding), 16)
        facts = self._facts(finding)

        # Prefer phrasings that can use the specifics we detected, but keep the
        # full pool so short and long variants stay in rotation.
        usable = [
            key for key in ("vague", "term", "phrase", "source", "sources", "date",
                            "examples", "stat", "opener", "long", "short")
            if str(facts.get(key) or "").strip()
        ]
        if usable:
            specific = [
                c for c in candidates
                if any("{" + key + "}" in c[0] + c[1] for key in usable)
            ]
            candidates = candidates + specific

        order = list(range(len(candidates)))
        start = digest % len(order)
        order = order[start:] + order[:start]

        last_len = self._lengths[-1] if self._lengths else None
        for strict in (True, False):
            for idx in order:
                lead, advice = candidates[idx]
                try:
                    lead_f = lead.format(**facts) if "{" in lead else lead
                    advice_f = advice.format(**facts) if "{" in advice else advice
                except (KeyError, IndexError):
                    continue
                opener = _slug(lead_f.split(".")[0])
                skeleton = _slug(lead)
                # Shape mix measured from the 307-comment corpus: 46% of notes are
                # a single sentence, 49% are two or three. Emit the observation
                # alone, the advice alone, or both, instead of always pairing them.
                shape = digest % 20
                if shape < 8:
                    parts = (lead_f,)
                else:
                    parts = (lead_f, advice_f)
                if len(parts) == 2 and advice_f:
                    # 39% of the corpus comments hedge ("a bit", "maybe", "seems").
                    if digest % 3 == 0:
                        advice_f = "Maybe " + advice_f[0].lower() + advice_f[1:]
                    elif digest % 7 == 0:
                        advice_f = "Perhaps " + advice_f[0].lower() + advice_f[1:]
                    # 11% of the corpus comments ask a question.
                    if digest % 5 == 0:
                        tail = _QUESTIONS[(digest >> 9) % len(_QUESTIONS)]
                        advice_f = advice_f.rstrip(". ") + ". " + tail
                text = _clean(" ".join(x for x in parts if x))
                if opener in self._used_openers and len(candidates) > 1:
                    continue
                if skeleton in self._used_skeletons and len(candidates) > 1:
                    continue
                key = _slug(text)
                if key in self._used_phrasings:
                    continue
                # Keep sentence lengths moving: don't place two notes of the same
                # size next to each other when another shape is available.
                if strict and last_len is not None and abs(len(text.split()) - last_len) < 6:
                    continue
                self._used_openers.add(opener)
                self._used_skeletons.add(skeleton)
                self._used_phrasings.add(key)
                text = self._maybe_extend(text, finding.category, digest)
                self._used_phrasings.add(_slug(text))
                self._lengths.append(len(text.split()))
                return text

        lead, advice = candidates[digest % len(candidates)]
        text = _clean(" ".join(x for x in (lead, advice) if x))
        self._lengths.append(len(text.split()))
        return text

    def _maybe_extend(self, text: str, category: str, digest: int) -> str:
        """Disabled: appended advice duplicated the sentence it followed.

        Human comments in the exemplars are one or two sentences. Length variety
        comes from the template variants instead of a bolted-on aphorism.
        """
        return text

    @staticmethod
    def scan_style(text: str) -> list[str]:
        low = text.lower()
        return [p for p in BANNED_PHRASES if p in low]


def compose_all(model: DocumentModel, selected: list[SelectedComment],
                essay_type: str) -> list[tuple[SelectedComment, str]]:
    composer = CommentComposer(model, essay_type)
    out: list[tuple[SelectedComment, str]] = []
    for item in selected:
        body = _strip_leading_label(composer.compose(item),
                                    item.category if item.labelled else "")
        out.append((item, body))
    return out


def _strip_leading_label(body: str, category: str) -> str:
    """Avoid 'THESIS STATEMENT THESIS STATEMENT ...' after the link is prepended."""
    if not category:
        return body
    match = re.match(rf"^{re.escape(category)}[\s:,\-\u2013\u2014]+", body, re.IGNORECASE)
    if not match:
        return body
    rest = body[match.end():]
    if rest[:1].isupper() or rest[:1] in "\u201c\"'":
        return rest
    return body

