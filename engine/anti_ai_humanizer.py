"""
Anti-AI Humanizer Engine for Academic Editorial Operations.
Legacy editorial helpers. No detector outcome or human authorship is promised.
Studio uses the guarded feedback-humanization stage before Word validation.
"""

import re
import math
from typing import List, Dict, Any, Tuple


# Strict blacklist of words and phrases that trigger AI classifiers
BANNED_AI_VOCABULARY = {
    "delve", "delving", "testament", "tapestry", "beacon", "paramount", "multifaceted",
    "commendable", "furthermore", "moreover", "in conclusion", "crucial role", "pivotal",
    "fosters", "fostering", "embarking", "vibrant", "nuance", "nuances", "nuanced",
    "interplay", "realm", "holistic tapestry", "a testament to", "plays a crucial role",
    "it is important to note", "it is worth noting", "sheds light on", "serves as a",
    "intricate", "pivotal role", "dynamic interplay", "underscores the importance",
    "unwavering dedication", "profound impact", "inextricably linked", "beacon of hope"
}

# Replacement idioms used by human professional editors
HUMAN_EDITORIAL_REPLACEMENTS = {
    "it is important to note": "Notice that",
    "it is worth noting": "Keep in mind:",
    "crucial role": "direct impact",
    "pivotal": "central",
    "furthermore": "Also,",
    "moreover": "What's more,",
    "in conclusion": "Finally,",
    "commendable": "solid",
    "multifaceted": "complex",
    "fosters": "builds",
    "delve into": "dig into",
    "delves into": "explores",
    "testament to": "proof of",
    "tapestry": "structure",
    "beacon": "model"
}


def measure_burstiness(text: str) -> Tuple[float, float, float]:
    """
    Computes sentence length mean, standard deviation, and burstiness ratio.
    These statistics describe rhythm; they do not identify human authorship.
    """
    sentences = [s.strip() for s in re.split(r'[.!?]+', text) if s.strip()]
    if not sentences:
        return 0.0, 0.0, 0.0
    lengths = [len(s.split()) for s in sentences]
    mean = sum(lengths) / len(lengths)
    variance = sum((l - mean) ** 2 for l in lengths) / len(lengths)
    std_dev = math.sqrt(variance)
    burstiness = std_dev / (mean + 1e-6)
    return mean, std_dev, burstiness


def sanitize_ai_vocabulary(text: str) -> str:
    """Preserve supplied prose; broad synonym substitutions can change advice."""
    return text


def inject_human_burstiness(sentences: List[str]) -> List[str]:
    """
    Compatibility helper: return the original sentences without invented remarks.
    """
    return list(sentences)


def humanize_editorial_comment(original_comment: str, author_role: str = "Trivium / ThinkingStorm Senior Reviewer") -> str:
    """
    Compatibility helper preserving the original diagnosis and reviewer register.
    """
    return original_comment.strip()


def build_thinkingstorm_tutor_overview(
    student_name: str,
    institution: str,
    prompt: str,
    word_count: int,
    scores: Dict[str, int],
    reviewer_name: str = "Academic Admissions Specialist",
    specific_observations: List[str] = None
) -> str:
    """
    Generates a full ThinkingStorm / Trivium style comprehensive Tutor Overview Letter
    with the legacy letter structure. No authorship-detector result is measured.
    """
    total_score = sum(scores.values())
    first_name = student_name.split()[0] if student_name else "Student"
    
    obs_text = ""
    if specific_observations:
        obs_bullets = "\n".join([f"• {obs}" for obs in specific_observations])
        obs_text = f"\nKey Priorities for Your Next Revision:\n{obs_bullets}\n"
    else:
        obs_text = f"""
Key Priorities for Your Next Revision:
• Opening Hook: Move away from broad universal claims ("Everyone goes to the doctor...") and open directly in media res with your hands-on CNA experience.
• Clinical Specificity: Ground your emotional reflections in sensory patient details. Don't just say you made a difference—show the bedside moment that proved it.
• Institutional Alignment: Tie your clinical observations directly into {institution}'s specific curriculum and philosophy.
"""

    letter = f"""THINKINGSTORM / TRIVIUM EDITORIAL REVIEW DESK
COMPREHENSIVE TUTOR OVERVIEW & REVISION BLUEPRINT
Submission ID: LECOM-FCC-2026 | Applicant: {student_name}
Target Program: {institution} | Word Count: {word_count} words
Evaluated Standard: 4-Pillar Non-Ghostwriting Pedagogical Matrix

Dear {first_name},

Thank you for submitting your essay draft for {institution}! You have chosen a demanding field, and your hands-on background as a Certified Nursing Assistant gives your statement genuine weight. Admissions committees look for applicants who already understand patient vulnerability. You clearly do.

That said, admissions officers review thousands of medical and healthcare essays every week. To make yours unforgettable, we need to sharpen your narrative focus. Right now, some of your strongest clinical insights get buried behind broad introductory statements and passive phrasing. In this review, I've left detailed inline marginal comments and line-edit suggestions to help you take this draft from a good second attempt to an interview-clinching personal statement.

{obs_text}
Review your tracked changes in the attached redline document carefully. Ask yourself on every paragraph: "Does this sound like an applicant talking about medicine, or does it sound like a future physician reflecting on clinical care?"

Best of luck with your revisions,

{reviewer_name}
Senior Admissions Specialist • ThinkingStorm / Apex Editorial Operations
"""
    return letter.strip()
