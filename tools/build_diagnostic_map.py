"""Build knowledge/diagnostic_map.json: KB diagnostic -> analyser rule.

Statuses:
  mapped     the analyser emits a finding that covers this diagnostic
  human_only the KB itself marks it semantic/external; no offline detector may
             claim it (plagiarism, fallacies, literary reading, source stance)
  no_rule    a mechanical/structural check the analyser does not implement yet
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KB = ROOT / "knowledge" / "thinkingstorm_kb_v2.json"
OUT = ROOT / "knowledge" / "diagnostic_map.json"

MAPPED: dict[str, list[str]] = {
    # thesis
    "THESIS_CLAIM": ["thesis_missing", "thesis_vague"],
    "THESIS_REASON": ["thesis_no_preview"],
    "THESIS_SCOPE": ["thesis_spread"],
    "THESIS_POSITION": ["thesis_missing"],
    # introduction
    "INTRO_STATUS": ["intro_generic"],
    "INTRO_PROBLEM": ["intro_generic"],
    "INTRO_STAKES": ["intro_generic"],
    "INTRO_HOOK": ["intro_generic"],
    # abstract
    "ABSTRACT_TYPE": ["abstract_intro"],
    "ABSTRACT_STANDALONE": ["abstract_intro"],
    "ABSTRACT_ELEMENTS": ["abstract_intro"],
    # organisation
    "BODY_STRUCTURE": ["para_no_claim", "topic_evidence_opener"],
    "OUTLINE_ORDER": ["paragraph_overlong", "para_drift"],
    # topic sentences
    "TOPIC_MAIN": ["para_no_claim", "topic_evidence_opener"],
    "TOPIC_THESIS": ["topic_evidence_opener"],
    # conclusion
    "CONCLUSION_SYNTHESIS": ["conclusion_summary", "conclusion_and_fragments",
                             "conclusion_and_punctuation", "conclusion_announced"],
    "CONCLUSION_NEW": ["conclusion_thin"],
    "CONCLUSION_STAKES": ["conclusion_thin"],
    # transitions
    "TRANSITION_LOGIC": ["transition_abrupt"],
    "TRANSITION_MISMATCH": ["transition_abrupt"],
    # evidence / statistics
    "EVIDENCE_CONTEXT": ["study_listing"],
    "EVIDENCE_SUPPORT": ["para_unsupported"],
    "EVIDENCE_ANALYSIS": ["evidence_no_analysis"],
    "STAT_RELEVANCE": ["evidence_no_analysis"],
    "STAT_CLARITY": ["evidence_no_analysis"],
    "STAT_INTERPRET": ["evidence_no_analysis"],
    # APA
    "APA_QUOTE_LOCATOR": ["quote_no_page"],
    "APA_REF_FORMAT": ["apa_database"],
    "APA_TITLE": ["apa_instructor_missing", "apa_course_name"],
    "APA_ABSTRACT": ["abstract_intro"],
    # MLA
    "MLA_HEADING": ["mla_heading_order", "mla_heading_same_line"],
    "MLA_HEADER": ["mla_header_missing"],
    "MLA_PARENT": ["mla_container_italics", "mla_raw_url_container"],
    "MLA_WORKS": ["works_cited_top_margin"],
    "MLA_TITLE": ["mla_title_case"],
    # grammar / clarity
    "GRAM_AGREEMENT": ["subject_verb"],
    "GRAM_COMMA_SPLICE": ["comma_splice"],
    "GRAM_FRAGMENT": ["fragment"],
    "GRAM_PASSIVE_AGENCY": ["para_passive"],
    "GRAM_PRONOUN_ANTECEDENT": ["vague_pronoun"],
    "GRAM_END_MARK": ["title_period"],
    "FORMAL_DICTION": ["informal_diction"],
    "PERSUASIVE_OPPOSITION": ["counterargument_missing"],
    "INTRO_HOOK": ["intro_generic", "statement_cliche_opener"],
    "THESIS_CLAIM": ["thesis_missing", "thesis_vague", "statement_generic_claim",
                     "thesis_rhetorical_missing", "thesis_and_grammar"],
}

HUMAN_ONLY: dict[str, str] = {
    "REVISION_PRIORITY": "editorial prioritisation, not a text feature",
    "TOPIC_COMPARE": "requires comparing two works named in the paragraph",
    "QUOTE_OVERUSE": "requires source/quotation boundary verification",
    "QUOTE_PARAPHRASE": "requires source text to compare wording",
    "QUOTE_SUMMARY": "requires source text to compare wording",
    "PLAGIARISM_WARNING": "external verification only; never asserted offline",
    "SOURCE_TYPE": "requires source metadata",
    "STAT_EXAGGERATION": "requires study sample and claim comparison",
    "APA_NARRATIVE_DATE": "requires reference list to resolve date",
    "APA_REF_MATCH": "requires full reference list reconciliation",
    "APA_REF_LAYOUT": "requires layout inspection of the reference list",
    "MLA_SPACING": "requires layout inspection (spacing/margins)",
    "MLA_QUOTE": "requires block-quotation layout and line count",
    "LOGIC_INDUCTION": "semantic reasoning",
    "LOGIC_DEDUCTION": "semantic reasoning",
    "LOGIC_CAUSATION": "semantic reasoning",
    "LOGIC_FALSE_CHOICE": "semantic reasoning",
    "LOGIC_STRAW": "semantic reasoning",
    "LOGIC_PICKING": "semantic reasoning",
    "BIAS_UNSUPPORTED": "semantic judgement",
    "BIAS_GROUPS": "semantic judgement with group sensitivity",
    "CHICAGO_STYLE": "no Chicago detector implemented",
    "CHICAGO_NOTES": "no Chicago detector implemented",
    "CHICAGO_SHORT": "no Chicago detector implemented",
    "CHICAGO_AUTHOR_DATE": "no Chicago detector implemented",
    "CHICAGO_LAYOUT": "no Chicago detector implemented",
    "ANNOT_SUMMARY": "no annotated-bibliography detector implemented",
    "ANNOT_CREDIBILITY": "requires source metadata",
    "ANNOT_RELEVANCE": "requires research question",
    "ANNOT_STRUCTURE": "no annotated-bibliography detector implemented",
    "RESEARCH_ARGUMENT": "semantic classification of research stance",
    "RESEARCH_ANALYTIC": "semantic classification of research stance",
    "RESEARCH_CONFIRMBIAS": "requires source corpus comparison",
    "SOCIAL_METHOD": "requires method section reading",
    "DESCRIPTIVE_SPECIFIC": "semantic judgement of descriptive detail",
    "BUSINESS_PURPOSE": "no cover-letter detector implemented",
    "BUSINESS_FIT": "requires job advert",
    "BUSINESS_END": "no cover-letter detector implemented",
    "NURSING_PRECISION": "clinical accuracy requires human review",
    "NURSING_VOICE": "clinical accuracy requires human review",
}

NO_RULE: dict[str, str] = {
    "GRAM_APOSTROPHE_USAGE": "no apostrophe parser",
    "GRAM_APPOSITIVE_PUNCTUATION": "no appositive parser",
    "GRAM_ARTICLE_SELECTION": "no article parser",
    "GRAM_CAPITALIZATION_CONSISTENCY": "no capitalisation rule",
    "GRAM_SEMICOLON_CLAUSES": "no semicolon parser",
    "GRAM_INTRODUCTORY_COMMA": "no introductory-comma rule",
    "GRAM_INDEPENDENT_CLAUSE_COMMA": "no clause parser",
    "GRAM_SUBORDINATE_CLAUSE": "no clause parser",
    "GRAM_COMPOUND_PUNCTUATION": "no clause parser",
    "GRAM_HYPHENATION": "no hyphenation rule",
    "GRAM_NARRATIVE_PERSON": "no point-of-view rule",
    "GRAM_VERBALS": "no verbals parser",
    "GRAM_HOMOPHONE": "no homophone dictionary",
    "GRAM_VERB_FORM": "no irregular-verb parser",
    "GRAM_DANGLING_MODIFIER": "no modifier parser",
    "GRAM_MISPLACED_MODIFIER": "no modifier parser",
    "GRAM_PARALLEL_STRUCTURE": "no parallelism rule",
    "GRAM_PART_OF_SPEECH": "no POS tagger",
    "GRAM_PREPOSITION_CHOICE": "no preposition rule",
    "GRAM_PRONOUN_CASE": "no pronoun-case rule",
    "GRAM_RUN_ON": "no run-on rule",
    "GRAM_TENSE_CONSISTENCY": "no tense rule",
}

LIT = {
    "LIT_THEME": "literary reading requires the text",
    "LIT_ALLEGORY": "literary reading requires the text",
    "LIT_CHARACTER": "literary reading requires the text",
    "LIT_IMAGERY": "literary reading requires the text",
    "LIT_LITOTES": "literary reading requires the text",
    "LIT_METONYMY": "literary reading requires the text",
    "LIT_PERSONIFICATION": "literary reading requires the text",
    "LIT_PLOT": "literary reading requires the text",
    "LIT_POV": "literary reading requires the text",
    "LIT_SETTING": "literary reading requires the text",
    "LIT_SIMILE": "literary reading requires the text",
    "LIT_STRUCTURE": "literary reading requires the text",
    "LIT_TONE_MOOD": "literary reading requires the text",
    "LIT_SYMBOLISM": "literary reading requires the text",
    "LIT_SYNECDOCHE": "literary reading requires the text",
}


def main() -> None:
    kb = json.loads(KB.read_text(encoding="utf-8"))
    human = {**HUMAN_ONLY, **LIT}
    entries = []
    for diagnostic in kb["diagnostics"]:
        did = diagnostic["id"]
        if did in MAPPED:
            status, rules, reason = "mapped", MAPPED[did], ""
        elif did in human:
            status, rules, reason = "human_only", [], human[did]
        elif did in NO_RULE:
            status, rules, reason = "no_rule", [], NO_RULE[did]
        else:
            raise SystemExit(f"unclassified diagnostic: {did}")
        entries.append({
            "id": did,
            "area": diagnostic["area"],
            "move_id": diagnostic["move_id"],
            "level": diagnostic["level"],
            "status": status,
            "rules": rules,
            "reason": reason,
        })

    missing = set(MAPPED) - {e["id"] for e in entries}
    if missing:
        raise SystemExit(f"mapped ids not in KB: {sorted(missing)}")

    rules = {r for e in entries for r in e["rules"]}
    unknown = sorted(r for r in rules if r not in _rules())
    if unknown:
        raise SystemExit(f"unknown analyser rules: {unknown}")

    OUT.write_text(json.dumps({"entries": entries}, indent=1), encoding="utf-8")
    counts = {}
    for entry in entries:
        counts[entry["status"]] = counts.get(entry["status"], 0) + 1
    print("wrote", OUT, counts, "mapped rules", len(rules))


def _rules() -> set[str]:
    import re

    src = (ROOT / "engine" / "review" / "analysis.py").read_text(encoding="utf-8")
    found = set(re.findall(r'Finding\(\s*"([a-z_]+)"', src))
    # rules produced by selection merging or template aliases
    found |= {"conclusion_and_fragments", "conclusion_and_punctuation", "thesis_and_grammar"}
    return found


if __name__ == "__main__":
    main()
