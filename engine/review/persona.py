"""Deterministic, rule-specific editorial comments.

Preserve each diagnosis and its revision advice as a complete unit. Variants
are reproducible; wording choices never remove advice or introduce a different
diagnosis. Nothing here calls a model or an authorship detector.
"""
from __future__ import annotations

import hashlib
import re
from string import Formatter
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

# Merge the knowledge base's banned list (v2) without losing the local one.
BANNED_PHRASES = list(BANNED_PHRASES)
try:
    from .kb import banned_phrases as _kb_banned_phrases

    for _phrase in _kb_banned_phrases():
        _low = _phrase.lower()
        if _low not in BANNED_PHRASES:
            BANNED_PHRASES.append(_low)
except Exception:  # the KB is optional rule data
    pass

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
        ("Please verify this publication year against the original source.",
         "An unusual year may be correct; change it only if the source gives a different date."),
    ],

    # -- abstract -----------------------------------------------------------
    "abstract_intro": [
        ("This reads like an introduction, not an abstract.",
         "Summarize the paper's purpose, main findings, and takeaway rather than only introducing the topic."),
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
        ("The paragraph reports the evidence without explaining its relevance to the claim.",
         "Once you present these findings, elaborate on what the data proves and how it supports the "
         "main claim."),
        ("The evidence arrives and the paragraph moves on before explaining it.",
         "Add a sentence or two on what this {source} result means for your argument."),
        ("This citation is doing the work of an argument by itself.",
         "Spell out what the reader should conclude from it."),
        ("The paragraph does not explain why this evidence matters to its claim.",
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
        ("Please check whether the passive wording makes the actor unclear.",
         "Use an active verb where naming the actor would help; retain the passive where the action is the focus."),
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
        ("This paragraph is long enough to warrant a check of its focus.",
         "If the discussion changes subject, start a new paragraph there and introduce its main point."),
        ("Please check whether this long paragraph develops one main point.",
         "Keep supporting details together; separate a new point only where the focus changes."),
    ],
    "mla_heading_same_line": [
        ("Each item in an MLA heading belongs on its own line.",
         "Put the instructor's name on the line below yours."),
        ("Two heading elements are typed on one line here.",
         "Separate them so name, instructor, course, and date each get a line."),
    ],
    "quote_no_page": [
        ('The source entry for {source} lists numbered pages, but this quotation has no page locator.',
         'Check the edition you used and cite the page containing the quoted words. Use only a number supplied by that source.'),
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
        ("Delete the extra space in front of this mark.",
         "Set the punctuation flush against the preceding word."),
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
        ("Separate the punctuation mark from the next word with a space.",
         "Insert a single space here to preserve the reading rhythm."),
        ("There is no space following this mark.",
         "Add a space so the two words are properly divided."),
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


from .pedagogy import TEMPLATES as _PEDAGOGY_TEMPLATES
TEMPLATES.update(_PEDAGOGY_TEMPLATES)
TEMPLATES.update({
    'thesis_missing': [
        ('The introduction describes the situation without setting out a focused position for the essay.',
         'What central claim should readers take from {anchor}? State that claim and identify the main points the body will develop.'),
        ('A central claim is still needed at the end of this introduction.',
         'Use the discussion in your body paragraphs to decide what position the essay will support. Then bring that position and its main reasons together in a focused thesis statement.'),
    ],
    'thesis_vague': [
        ('The thesis here is broad enough that the reader still has to infer the direction of the argument.',
         'Could you identify the specific position you will support and the reasons behind it? Check that those reasons match the discussion in the body.'),
    ],
    'thesis_no_preview': [
        ('The thesis states a position, but it does not yet prepare readers for the points that follow.',
         'Name the main reasons or comparisons the body will develop, and place them in the same order. This will give the opening a clearer direction.'),
    ],
    'transition_abrupt': [
        ('The move into this paragraph leaves the relationship to the previous point unstated.',
         'Could you explain whether this idea adds a reason, introduces a contrast or follows from the earlier discussion? Build that relationship into the opening instead of adding a transition word on its own.'),
    ],
    'topic_evidence_opener': [
        ('The paragraph opens with a source or result before identifying the point it will support.',
         'Add a topic sentence in your own words that establishes the paragraph’s focus. Then introduce the evidence and explain how it supports that point.'),
    ],
    'para_no_claim': [
        ('This opening reports background information, while the point of the paragraph is left implicit.',
         'Could you name the main idea you want to develop here and explain its relation to the essay’s central focus? Let the supporting detail follow that idea.'),
    ],
})

TEMPLATES.update({
    'mla_heading_alignment': [
        ('Headings in MLA sit flush left; centering the name block makes the page read as a title page rather than a heading.',
         'Left-align the four heading lines and keep them double-spaced.'),
        ('This heading block is centered, but MLA aligns it to the left margin.',
         'Set the four heading lines flush left, in the same order.'),
    ],
    'formulaic_opinion': [
        ('You introduce your own reading with “{phrase}” in {count} places, which makes the analysis sound recited rather than considered.',
         'Keep the strongest instance and vary the others: name what the detail shows before you interpret it.'),
        ('“{phrase}” recurs {count} times across the essay.',
         'Replace the later instances with a direct statement of what the evidence suggests.'),
    ],
    'paragraph_short': [
        ('This paragraph closes before the idea is developed.',
         'Either fold it into the surrounding paragraph or add the evidence and explanation it needs to stand on its own.'),
        ('This paragraph reads as a fragment of a thought.',
         'Develop the claim with a source or an example, or merge it upward.'),
        ('A brief section like this needs fuller explanation to support its point.',
         'Supply the necessary evidence and analysis here, or combine this passage with the adjacent paragraph.'),
        ('The thought stops before the reasoning is fully laid out.',
         'Bring in specific detail to substantiate the claim, or merge these sentences into the previous paragraph.'),
        ('This short passage leaves its main point undeveloped.',
         'Expand on what this idea contributes to the overall paper, or attach it to the surrounding discussion.'),
        ('Consider whether this brief point can stand independently.',
         'Add the missing context and analytical follow-through, or integrate the sentence into the neighboring paragraph.'),
    ],
    'common_misspelling': [
        ('“{wrong}” is misspelled.', 'Correct it to “{right}”.'),
        ('This should read “{right}”, not “{wrong}”.', ''),
    ],
    'reference_missing_period': [
        ('Works Cited entries end with a period, including after a URL or page range.',
         'Add the closing period to this entry.'),
        ('This entry stops without terminal punctuation.',
         'Close it with a period, as the style requires for every entry.'),
        ('Every citation entry closes with a final period.',
         'Place a period at the very end of this source reference.'),
        ('A terminal period is missing at the conclusion of this entry.',
         'Insert a period after the closing characters to complete the citation.'),
        ('Reference list entries require closing punctuation.',
         'End this entry with a period so it matches the format of the remaining references.'),
        ('The final mark is missing from this reference entry.',
         'Add the concluding period to complete the citation.'),
    ],
})

TEMPLATES.update({
    'paragraph_overlong': [
        ('This long paragraph would benefit from a check of its focus around {anchor}.',
         'Identify the main point and keep its supporting details together. If the discussion changes to a different point, start a new paragraph there and introduce that point explicitly.'),
        ('Read the paragraph containing {anchor} as a sequence of main point, evidence and explanation.',
         'Mark a possible break only where you begin developing a separate point, and check that the next paragraph would have its own clear opening.'),
        ('The discussion around {anchor} covers multiple distinct points in a single block.',
         'Separate the secondary idea into its own paragraph so readers can absorb each claim in turn.'),
        ('Consider a paragraph break near {anchor} to maintain clarity.',
         'Keep the initial focus in the first paragraph, and open the new paragraph with a clear transitional claim.'),
    ],
    'thesis_long': [
        ('The thesis packs several ideas into one long sentence.',
         'Identify the central claim and the main points that support it. Keep those elements in the thesis, and move background explanation or secondary detail into the body so the argument is easier to follow.'),
    ],
    'evidence_no_analysis': [
        ('The paragraph presents evidence, but its connection to the paragraph’s point needs explanation.',
         'After {anchor}, explain which detail supports your interpretation and why. Keep that explanation within what the source establishes, then connect it to the claim you are developing.'),
        ('The source is reported here without enough discussion of what readers should take from it.',
         'What does {anchor} show about your paragraph’s main point? Explain that connection in your own words before introducing another source or moving to the next idea.'),
    ],
    'repeated_opener': [
        ('These two paragraphs begin with the same “{opener}” construction.',
         'Rework this opening around the specific point this paragraph adds. Show its relationship to the preceding idea, rather than replacing the repeated wording with an unrelated transition word.'),
    ],
    'conclusion_summary': [
        ('The ending returns to points already discussed in the body.',
         'Use those points to explain the overall significance of the argument. What should readers understand or reconsider after this discussion? Develop that takeaway without introducing a new claim that still needs evidence.'),
    ],
    'conclusion_thin': [
        ('This brief ending needs more explanation of how the essay’s points fit together.',
         'Draw a connection between the main ideas already developed in the body. Then explain what that connection reveals about the topic, so the final paragraph offers readers a clear takeaway.'),
    ],
    'conclusion_and_punctuation': [
        ('The ending returns to earlier points and also contains a marked punctuation issue.',
         'First explain how the main points fit together and why that connection matters to readers. Then correct the punctuation in the marked passage and reread the complete sentence to check its meaning.'),
    ],
    'statistics_no_analysis': [
        ('The significance of {stat} needs explanation alongside the number.',
         'Identify what the figure measures and the comparison or context needed to interpret it. Then explain how it supports the paragraph’s point, keeping your conclusion within what the reported evidence shows.'),
    ],
})

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


class CompositionError(ValueError):
    """A finding has no complete, rule-specific wording."""


def classify_opener_archetype(text: str) -> str:
    clean = text.strip()
    if re.search(r"^(Cut|Replace|Move|Delete|Trim|Omit|Drop|Swap|Spell|Change|Write|Reorder)\b.*[\"“]", clean, re.I):
        return "imperative_quote"
    if re.search(r"^(Why|Which|How|What|Where|Could)\b", clean, re.I) and "?" in clean:
        return "socratic_check"
    if re.search(r"^(You open with|Although|While|Whereas|Even though|You state)\b", clean, re.I):
        return "contrastive_claim"
    if re.search(r"^(If you want|When you revise|Should you|If the|When you|Once you)\b", clean, re.I):
        return "conditional_fix"
    if re.search(r"^[A-Z][a-z]+(?:\s+[a-z]+){0,4}[.:]\s+[A-Z]", clean):
        return "fragment_diagnosis"
    if re.search(r"^(A reader|The reader|After|Without|Readers?)\b", clean, re.I):
        return "reader_anchor"
    return "default"


_SYNONYM_SLOTS: list[tuple[re.Pattern, tuple[str, ...]]] = [
    (re.compile(r"\bin your own words\b", re.I), ("in your own words", "in your own phrasing", "using your own phrasing", "in direct terms")),
    (re.compile(r"\bmain points\b", re.I), ("main points", "core points", "key points", "central points")),
    (re.compile(r"\bsupporting details\b", re.I), ("supporting details", "supporting material", "evidence and details", "specific details")),
    (re.compile(r"\bcentral claim\b", re.I), ("central claim", "main claim", "core position", "governing claim")),
    (re.compile(r"\bfor the reader\b", re.I), ("for the reader", "for readers", "for your reader", "for an outside reader")),
    (re.compile(r"\bthe reader\b", re.I), ("the reader", "readers", "your reader", "a reader")),
    (re.compile(r"\bbody paragraphs\b", re.I), ("body paragraphs", "body sections", "supporting paragraphs", "main paragraphs")),
    (re.compile(r"\bin the body\b", re.I), ("in the body", "across the body", "in the main paragraphs", "through the body")),
    (re.compile(r"\bthis paragraph\b", re.I), ("this paragraph", "the paragraph here", "this section", "this passage")),
    (re.compile(r"\bthe paragraph's\b", re.I), ("the paragraph's", "this paragraph's", "the section's", "this passage's")),
    (re.compile(r"\bthe paragraph’s\b", re.I), ("the paragraph’s", "this paragraph’s", "the section’s", "this passage’s")),
    (re.compile(r"\bexplain how\b", re.I), ("explain how", "show how", "clarify how", "spell out how")),
    (re.compile(r"\bmake sure\b", re.I), ("make sure", "check that", "verify that", "confirm that")),
    (re.compile(r"\bthis source entry\b", re.I), ("this source entry", "the reference entry here", "this citation entry", "the entry here")),
    (re.compile(r"\bhas an? (?:explicit|custom)?\s*spacing (?:setting|override)\b", re.I), ("has an explicit spacing setting", "carries a custom spacing override", "uses an explicit spacing setting", "has a spacing override")),
    (re.compile(r"\bis not double spacing\b", re.I), ("is not double spacing", "differs from double spacing", "does not use double spacing", "is not set to double spacing")),
    (re.compile(r"\bset the entry to double spacing\b", re.I), ("set the entry to double spacing", "change this entry to double spacing", "format the entry with double spacing", "apply double spacing here")),
    (re.compile(r"\bapply the same setting\b", re.I), ("apply the same setting", "apply this formatting", "keep the same spacing", "use the same setting")),
    (re.compile(r"\bto the other entries\b", re.I), ("to the other entries", "to the remaining entries", "to the surrounding entries", "to the other references")),
    (re.compile(r"\brather than inserting\b", re.I), ("rather than inserting", "instead of inserting", "without adding", "rather than adding")),
    (re.compile(r"\bbetween wrapped lines\b", re.I), ("between wrapped lines", "across wrapped lines", "between lines", "within wrapped lines")),
    (re.compile(r"\bparagraph formatting\b", re.I), ("paragraph formatting", "paragraph spacing controls", "Word paragraph settings", "paragraph line spacing")),
]


def _unquoted_5grams(text: str) -> set[tuple[str, ...]]:
    from .anti_ai_patterns import _mask_protected_spans

    masked, _ = _mask_protected_spans(text)
    masked = re.sub(r"__PROTECTED_SPAN_\d+__", " ", masked)
    words = re.findall(r"[a-z']+", masked.lower())
    if len(words) < 5:
        return set()
    return {tuple(words[i:i + 5]) for i in range(len(words) - 4)}


def _perturb_slots(text: str, seed_key: str) -> str:
    """Deterministically perturb high-frequency review phrase slots outside quotes."""
    from .anti_ai_patterns import _mask_protected_spans, _unmask_protected_spans

    masked, spans = _mask_protected_spans(text)
    for slot_idx, (pattern, choices) in enumerate(_SYNONYM_SLOTS):
        def _repl(match: re.Match, idx: int = slot_idx, opts: tuple[str, ...] = choices) -> str:
            h = hashlib.sha1(f"{seed_key}|slot:{idx}|{match.start()}".encode("utf-8")).digest()
            picked = opts[int.from_bytes(h[:4], "big") % len(opts)]
            orig = match.group(0)
            if orig and orig[0].isupper():
                return picked[0].upper() + picked[1:]
            return picked

        masked = pattern.sub(_repl, masked)
    return _unmask_protected_spans(masked, spans)


class CommentComposer:
    """Compose comment bodies for selected findings."""

    def __init__(self, model: DocumentModel, essay_type: str = "academic"):
        self.model = model
        self.essay_type = essay_type
        self._used_openers: set[str] = set()
        self._used_phrasings: set[str] = set()
        self._used_skeletons: set[str] = set()
        self._used_5grams: set[tuple[str, ...]] = set()
        self._prev_len: int = 0
        self._prev_archetype: str = ""
        self._recent_openers: list[str] = []
        self._comment_index: int = 0

    def _facts(self, finding) -> dict[str, Any]:
        facts = dict(finding.facts)
        anchor_words = list(re.finditer(r"\S+", finding.quote))
        anchor = finding.quote if len(anchor_words) <= 12 else finding.quote[:anchor_words[11].end()] + '…'
        facts.setdefault('anchor', '“' + anchor.strip() + '”')
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
        if rule == 'thesis_vague' and finding.facts.get('vague'):
            candidates = [('The wording {vague} leaves part of this thesis open to interpretation.',
                           'Name the particular idea or relationship you mean there. Keep the position and supporting points you have already stated, and revise the general wording so readers know exactly what the body will explain.')]
        if rule == 'informal_diction' and finding.facts.get('term') in {'things', 'stuff'}:
            candidates = [('“{term}” leaves the intended meaning open.',
                           'Name the specific issue, action or outcome you mean so the reader does not have to infer it from the surrounding discussion.')]
        if rule == "evidence_no_analysis" and finding.category == "STATISTICS":
            candidates = TEMPLATES.get("statistics_no_analysis", candidates)
        if rule == "typo_cluster" and not finding.facts.get("examples"):
            candidates = TEMPLATES.get("typo_spacing", candidates)
        if not candidates:
            raise CompositionError(f"no editorial template for rule {rule}")

        facts = self._facts(finding)
        rendered: list[tuple[str, str, str]] = []
        for lead, advice in candidates:
            try:
                slots = {name for _, name, _, _ in Formatter().parse(lead + advice)
                         if name is not None}
                if any(not str(facts.get(name) or "").strip() for name in slots):
                    continue
                rendered.append((lead.format(**facts), advice.format(**facts), lead))
            except (KeyError, IndexError, ValueError):
                continue
        # Knowledge-base patterns for the matching move. Anchored/specific ones
        # are preferred; generic ones only add variety at the end of the pool.
        try:
            from .kb import patterns_for_rule

            kb_specific, kb_generic = patterns_for_rule(rule, self.model, finding)
        except Exception:
            kb_specific, kb_generic = [], []
        # KB strings have already been filled. Formatting them a second time
        # would interpret braces in a student's quoted text as template slots.
        rendered.extend((lead, advice, lead) for lead, advice in kb_specific + kb_generic
                        if advice)
        if not rendered:
            raise CompositionError(f"no complete editorial template for rule {rule}")

        from .anti_ai_patterns import scrub_ai_tells
        from .selection import RHETORICAL
        from .analysis import ANALYSIS, STATISTICS

        variant_key = self._variant_key(finding)
        digest = int(variant_key, 16)
        start = digest % len(rendered)
        ordered = rendered[start:] + rendered[:start]

        dev_categories = RHETORICAL | {ANALYSIS, STATISTICS}
        is_developmental = (
            selected.category.split(" AND ")[0] in dev_categories
            and finding.facts.get("kind") != "strength"
        )
        allow_slot_perturbation = rule not in {"mla_date_numeric", "apa_date_numeric"}

        # Build expanded candidate pool with deterministic slot perturbations
        evaluated: list[tuple[float, int, str, str, str]] = []
        has_dev_length = any(
            len(_clean(" ".join(p for p in (l, a) if p)).split()) >= 25
            for l, a, _ in ordered
        )

        for rank_idx, (lead, advice, skeleton) in enumerate(ordered):
            base_full = _clean(" ".join(part for part in (lead, advice) if part))
            variants_to_try = range(4) if allow_slot_perturbation else range(1)
            for v_idx in variants_to_try:
                seed_str = f"{variant_key}|{self._comment_index}|v{v_idx}"
                perturbed = _perturb_slots(base_full, seed_str) if v_idx > 0 else base_full
                scrubbed = scrub_ai_tells(perturbed, seed=int(digest % 100000) + v_idx)
                words_count = len(scrubbed.split())
                arch = classify_opener_archetype(scrubbed)
                opener_bigram = " ".join(re.findall(r"[a-z']+", scrubbed.lower())[:2])
                grams = _unquoted_5grams(scrubbed)
                gram_overlap = len(grams & self._used_5grams)

                penalty = 0.0
                if _slug(lead) in self._used_openers:
                    penalty += 10.0
                if _slug(skeleton) in self._used_skeletons:
                    penalty += 10.0
                if _slug(scrubbed) in self._used_phrasings:
                    penalty += 25.0
                if gram_overlap:
                    penalty += 30.0 * gram_overlap

                if is_developmental and has_dev_length and words_count < 25:
                    penalty += 12.0

                if self._prev_archetype and arch == self._prev_archetype:
                    penalty += 4.0
                if opener_bigram and opener_bigram in self._recent_openers:
                    penalty += 3.0
                if self._prev_len > 0 and abs(words_count - self._prev_len) < 10:
                    penalty += 2.5

                # Alternate target length band (short/medium vs expanded) across comments
                if self._prev_len >= 34 and words_count >= 34:
                    penalty += 2.0
                elif 0 < self._prev_len <= 24 and words_count <= 24:
                    penalty += 2.0

                evaluated.append((penalty, rank_idx * 4 + v_idx, scrubbed, lead, skeleton))

        _, _, text, chosen_lead, chosen_skeleton = min(evaluated, key=lambda item: (item[0], item[1]))

        self._prev_len = len(text.split())
        self._prev_archetype = classify_opener_archetype(text)
        opener_bigram = " ".join(re.findall(r"[a-z']+", text.lower())[:2])
        if opener_bigram:
            self._recent_openers.append(opener_bigram)
            if len(self._recent_openers) > 3:
                self._recent_openers.pop(0)

        self._used_openers.add(_slug(chosen_lead))
        self._used_skeletons.add(_slug(chosen_skeleton))
        self._used_phrasings.add(_slug(text))
        self._used_5grams.update(_unquoted_5grams(text))
        self._comment_index += 1
        return text

    @staticmethod
    def scan_style(text: str) -> list[str]:
        low = text.lower()
        return [p for p in BANNED_PHRASES if p in low]


_SHORT_CADENCE_CHECKS = (
    "What changes here?",
    "Check every line.",
    "Which detail proves this?",
    "Test that link directly.",
    "Keep the focus tight.",
    "Where does that shift?",
    "Does the source agree?",
    "Cut any extra words.",
)


def _heal_cadence(
    model: DocumentModel,
    composed: list[tuple[SelectedComment, str]],
) -> list[tuple[SelectedComment, str]]:
    """Pre-write deterministic cadence pass ensuring CV >= 0.42 and bursty sentence lengths."""
    if len(composed) < 3:
        return composed

    from .style_guard import burstiness

    bodies = [b for _, b in composed]
    mean, std = burstiness(" ".join(bodies))
    cv = (std / mean) if mean > 0 else 0.0
    if cv >= 0.42 and std >= 2.6:
        return composed

    healed = list(composed)
    fp = getattr(model, "fingerprint", "") or "doc"
    used_5grams: set[tuple[str, ...]] = set()
    for _, b in healed:
        used_5grams.update(_unquoted_5grams(b))

    for idx in range(len(healed)):
        item, body = healed[idx]
        if item.finding.rule_id in {"mla_date_numeric", "apa_date_numeric"}:
            continue
        words = body.split()
        if not (16 <= len(words) <= 78):
            continue
        digest = int(hashlib.sha1(f"{fp}|cadence|{idx}".encode("utf-8")).hexdigest()[:8], 16)
        short_tag = _SHORT_CADENCE_CHECKS[digest % len(_SHORT_CADENCE_CHECKS)]
        if short_tag.lower() in body.lower():
            continue
        candidate = f"{body} {short_tag}"
        new_grams = _unquoted_5grams(candidate) - _unquoted_5grams(body)
        if new_grams & used_5grams:
            continue
        healed[idx] = (item, candidate)
        used_5grams.update(new_grams)
        new_bodies = [b for _, b in healed]
        m2, s2 = burstiness(" ".join(new_bodies))
        cv2 = (s2 / m2) if m2 > 0 else 0.0
        if cv2 >= 0.42 and s2 >= 2.6:
            break

    return healed


def compose_all(model: DocumentModel, selected: list[SelectedComment],
                essay_type: str) -> list[tuple[SelectedComment, str]]:
    composer = CommentComposer(model, essay_type)
    out: list[tuple[SelectedComment, str]] = []
    for item in selected:
        body = _strip_leading_label(composer.compose(item),
                                    item.category if item.labelled else "")
        out.append((item, body))
    return _heal_cadence(model, out)


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

