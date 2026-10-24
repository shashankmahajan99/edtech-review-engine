"""Build a paste-ready brief for an external model (ChatGPT / Astra).

The brief contains: the task, the measured corpus profile, a stratified sample of
real comments with their anchored text, the three human endnote letters, and the
exact JSON schema we can implement.

    python tools/export_astra_brief.py
    python tools/export_astra_brief.py --out docs/ASTRA_BRIEF.md
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from lxml import etree  # noqa: E402

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
CORPUS = ROOT / "style_corpus" / "voice_corpus.json"
PROFILE = ROOT / "style_corpus" / "voice_profile.json"

ENDNOTE_CANDIDATES = [
    Path(r"C:\Users\shashank\Downloads\janeen_REV_BY_TS_RaunakB_243347_1.docx"),
    Path(r"C:\Users\shashank\Downloads\andrea goblet.docx"),
    Path(r"C:\Users\shashank\Downloads\kiran mitra.docx"),
]

SCHEMA = {
    "persona": {
        "register": "one paragraph",
        "stance": "one paragraph",
        "habits": ["short bullets"],
        "never": ["short bullets"],
    },
    "moves": [
        {
            "id": "thesis",
            "labels": ["THESIS STATEMENT"],
            "patterns": [
                {
                    "observation": "sentence with {quote} / {term} / {source} slots",
                    "advice": "sentence or empty string",
                    "length": "short|medium|long",
                }
            ],
        }
    ],
    "anti_ai_rules": ["imperative rules grounded in the corpus"],
    "endnote_template": {
        "opening": "one or two sentences",
        "sections": [{"heading": "Thesis and overall focus", "pattern": "2-4 sentences with slots"}],
        "closing": "one sentence",
        "signoff": "All the best.",
    },
    "banned_phrases": ["words and constructions to reject"],
}


def endnote_texts() -> list[tuple[str, str]]:
    found = []
    for path in ENDNOTE_CANDIDATES:
        if not path.exists():
            continue
        try:
            with zipfile.ZipFile(path) as z:
                if "word/endnotes.xml" not in z.namelist():
                    continue
                root = etree.fromstring(z.read("word/endnotes.xml"))
            for note in root.findall(f"{W}endnote"):
                if note.get(f"{W}id") in {"-1", "0"}:
                    continue
                text = "\n".join(
                    "".join(p.itertext()).strip() for p in note.findall(f"{W}p")
                ).strip()
                if text:
                    found.append((path.name, text))
        except Exception:
            continue
    return found


def stratified(comments: list[dict], limit: int = 64) -> list[dict]:
    by_label: dict[str, list[dict]] = defaultdict(list)
    for c in comments:
        by_label[(c.get("label") or "UNLABELLED").upper()].append(c)

    picked: list[dict] = []
    seen: set[str] = set()

    def add(items):
        for item in items:
            key = item["body"][:80]
            if key not in seen:
                seen.add(key)
                picked.append(item)

    for label, items in sorted(by_label.items(), key=lambda kv: -len(kv[1]))[:10]:
        random.Random(label).shuffle(items)
        add(items[:3])

    questions = [c for c in comments if "?" in c["body"]]
    hedged = [c for c in comments if re.search(r"\b(a bit|a little|maybe|perhaps|seems)\b",
                                              c["body"].lower())]
    shortest = sorted(comments, key=lambda c: len(c["body"].split()))[:8]
    longest = sorted(comments, key=lambda c: -len(c["body"].split()))[:6]
    specific = [c for c in comments if re.search(r"[\u201c\"].{3,}[\u201d\"]", c["body"])]

    for group in (questions, hedged, specific, shortest, longest):
        add(group[:6])
    return picked[:limit]


def build(profile: dict, corpus: dict) -> str:
    comments = corpus["comments"]
    samples = stratified(comments)
    letters = endnote_texts()

    lines = [
        "# Voice brief: deterministic review-comment generator",
        "",
        "You are helping design the voice of an offline, deterministic review engine for an",
        "academic editing service. It writes margin comments and one endnote letter per",
        "student draft. No model runs at generation time, so your output must be reusable",
        "rules and patterns, not example prose alone.",
        "",
        "Your advice will be implemented as code. Be concrete and prescriptive, and ground",
        "every rule in the corpus below rather than in general writing advice.",
        "",
        "## Task",
        "",
        "Produce one JSON object with exactly these keys: `persona`, `moves`,",
        "`anti_ai_rules`, `endnote_template`, `banned_phrases`. Schema:",
        "",
        "```json",
        json.dumps(SCHEMA, indent=2),
        "```",
        "",
        "Requirements:",
        "",
        "- 12–16 `moves` covering thesis, introduction, abstract, evidence, analysis,",
        "  statistics, transitions, topic sentences, organisation, conclusion, grammar,",
        "  citations/formatting (APA and MLA), and sentence clarity.",
        "- 4–6 `patterns` per move, each a reusable observation/advice pair with slots",
        "  such as `{quote}`, `{term}`, `{source}`, `{count}`. Patterns must sound like",
        "  the reviewers below, not like a writing centre handout.",
        "- `anti_ai_rules`: at least 8 rules that a detector would notice if broken,",
        "  explicitly tied to the measured distribution below.",
        "- Keep the constraints: the corpus uses **no contractions**, rare first person,",
        "  46% one-sentence comments, and hedges in 39% of comments.",
        "- No generic praise, no sentence-length uniformity, no throat-clearing.",
        "- Return only the JSON in a fenced ```json block, no commentary.",
        "",
        "## Measured profile (307 comments, 25 documents, 2 reviewers)",
        "",
        "```json",
        json.dumps({k: profile[k] for k in (
            "documents", "comments", "comment_words", "sentence_lengths",
            "sentences_per_comment", "question_rate", "contraction_rate",
            "first_person_rate", "directive_rate", "hedge_rate", "specific_rate",
            "one_sentence_rate", "two_or_three_sentence_rate", "top_labels",
        ) if k in profile}, indent=2, ensure_ascii=False),
        "```",
        "",
        "## Representative comments (verbatim, with the anchored student text)",
        "",
    ]
    for c in samples:
        quote = re.sub(r"\s+", " ", c.get("quote", "")).strip()[:180]
        body = re.sub(r"\s+", " ", c["body"]).strip()
        label = c.get("label") or ""
        lines.append(f"- **{label or '—'}** · quote: “{quote}”")
        lines.append(f"  comment: {body}")
    lines += ["", "## Human endnote letters", ""]
    if letters:
        for name, text in letters:
            lines.append(f"### {name}")
            lines.append("")
            lines.append(text)
            lines.append("")
    else:
        lines.append("_No letters found at the expected paths; ask the operator to supply them._")
        lines.append("")
    lines += [
        "## What the operator will do with your answer",
        "",
        "The JSON is converted into template banks in `engine/review/persona.py` and",
        "`engine/review/endnote.py`, then validated against the distribution bands above.",
        "Patterns with slots must be usable verbatim: write sentences that read naturally",
        "whether the slot is a word, a phrase, or a full quotation.",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(ROOT / "docs" / "ASTRA_BRIEF.md"))
    args = parser.parse_args()
    profile = json.loads(PROFILE.read_text(encoding="utf-8"))
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    text = build(profile, corpus)
    out = Path(args.out)
    out.write_text(text, encoding="utf-8")
    print(f"wrote {out} ({len(text.split())} words)")


if __name__ == "__main__":
    main()
