"""ThinkingStorm knowledge-base link map.

Every label a comment can carry maps to a verified knowledge-base article.
Links are static: no network call is made at review time, and
:mod:`engine.review.validate` checks that only allow-listed URLs are written.
"""
from __future__ import annotations

BASE = "https://knowledge.thinkingstorm.com"
ALLOWED_PREFIX = BASE + "/"

LINKS: dict[str, str] = {
    "THESIS STATEMENT": f"{BASE}/PlanningOrganizing/ThesisStatements.aspx",
    "THESIS STATEMENTS": f"{BASE}/PlanningOrganizing/ThesisStatements.aspx",
    "INTRODUCTION": f"{BASE}/PlanningOrganizing/Introductions.aspx",
    "INTRODUCTIONS": f"{BASE}/PlanningOrganizing/Introductions.aspx",
    "ORGANISATION": f"{BASE}/PlanningOrganizing.aspx",
    "ORGANIZATION": f"{BASE}/PlanningOrganizing.aspx",
    "PLANNING & ORGANIZING": f"{BASE}/PlanningOrganizing.aspx",
    "TOPIC SENTENCE": f"{BASE}/PlanningOrganizing/TopicSentences.aspx",
    "TOPIC SENTENCES": f"{BASE}/PlanningOrganizing/TopicSentences.aspx",
    "TRANSITION": f"{BASE}/ArgumentClarity/Transitions.aspx",
    "TRANSITIONS": f"{BASE}/ArgumentClarity/Transitions.aspx",
    "ANALYSIS OF EVIDENCE": f"{BASE}/SourcesEvidence.aspx",
    "EVIDENCE": f"{BASE}/SourcesEvidence.aspx",
    "SOURCES & EVIDENCE": f"{BASE}/SourcesEvidence.aspx",
    "STATISTICS": f"{BASE}/SourcesEvidence.aspx",
    "ANALYSIS": f"{BASE}/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "COUNTER-ARGUMENT": f"{BASE}/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "COUNTERARGUMENT": f"{BASE}/WritingGuides/InformativeDescriptiveandPersuasiveWriting.aspx",
    "CONCLUSION": f"{BASE}/PlanningOrganizing/Conclusions.aspx",
    "CONCLUSIONS": f"{BASE}/PlanningOrganizing/Conclusions.aspx",
    "SUBJECT-VERB AGREEMENT": f"{BASE}/GrammarMechanicsandPunctuation/SubjectVerbAgreement.aspx",
    "SUBJECT VERB AGREEMENT": f"{BASE}/GrammarMechanicsandPunctuation/SubjectVerbAgreement.aspx",
    "PUNCTUATION": f"{BASE}/GrammarMechanicsandPunctuation/Commas.aspx",
    "COMMAS": f"{BASE}/GrammarMechanicsandPunctuation/Commas.aspx",
    "SENTENCE CLARITY": f"{BASE}/ArgumentClarity/SentenceClarity.aspx",
    "FRAGMENTS": f"{BASE}/GrammarMechanicsandPunctuation.aspx",
    "RUN-ON SENTENCES": f"{BASE}/GrammarMechanicsandPunctuation.aspx",
    "RUN-ONS": f"{BASE}/GrammarMechanicsandPunctuation.aspx",
    "INFORMAL WRITING": f"{BASE}/WritingGuides/FormalWriting.aspx",
    "MLA": f"{BASE}/APAMLAandChicagoTurabianFormatting.aspx",
    "APA": f"{BASE}/APAMLAandChicagoTurabianFormatting.aspx",
    "FORMATTING": f"{BASE}/APAMLAandChicagoTurabianFormatting.aspx",
    "FORMAL WRITING": f"{BASE}/WritingGuides/FormalWriting.aspx",
    "ABSTRACT": f"{BASE}/WritingGuides/WritinganAbstract.aspx",
}

FALLBACK = f"{BASE}/PlanningOrganizing.aspx"


def link_for(category: str, model=None) -> str:
    key = (category or "").strip().upper()
    if key in LINKS:
        return LINKS[key]
    # Multi-label comments such as "CONCLUSION AND FRAGMENTS" get the first
    # recognised label's article.
    for part in key.split(" AND "):
        part = part.strip()
        if part in LINKS:
            return LINKS[part]
    return FALLBACK


def is_allowed(url: str) -> bool:
    return isinstance(url, str) and url.startswith(ALLOWED_PREFIX)
