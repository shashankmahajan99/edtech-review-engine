"""Mine the reviewer corpus into measurable voice statistics.

Reads every reviewed .docx in the supplied folder, extracts native comments and
endnote letters, and writes:

  style_corpus/voice_corpus.json   every comment/endnote with its source
  style_corpus/voice_profile.json  the statistics the composer is tuned to
  docs/VOICE_PROFILE.md            a readable summary of those statistics

Usage:
    python tools/mine_voice_corpus.py "C:\\path\\to\\Doc examples"
"""
from __future__ import annotations

import json
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.extract_review import extract  # noqa: E402
from tools.endnote_extract import body_letter, paragraphs  # noqa: E402

CORPUS_DIR = ROOT / "style_corpus"

LABEL_RE = re.compile(r"^(?P<label>[A-Z][A-Za-z&/\- ]{2,60}?)\s*[-\u2013:]\s*")

BANNED = [
    "delve", "moreover", "furthermore", "in conclusion", "overall,", "crucial",
    "comprehensive", "nuanced", "multifaceted", "tapestry", "underscore",
    "pivotal", "leverage", "robust", "seamless", "holistic", "foster",
    "navigate", "realm", "landscape", "it is important to note",
    "plays a vital role", "a testament to",
]

HEDGES = [
    "a bit", "a little", "pretty ", "maybe", "perhaps", "seems", "slightly",
    "somewhat", "might", "could", "sort of", "kind of", "fairly", "rather",
]

FIRST_PERSON = [r"\bI\b", r"\bI'd\b", r"\bI'm\b", r"\bmy\b", r"\bme\b"]
DIRECTIVES = ["try", "consider", "make sure", "add ", "use ", "check ", "reread",
              "revise", "replace", "cut ", "move ", "clarify", "explain"]
CONTRACTIONS = re.compile(r"\b(?:don't|doesn't|isn't|aren't|can't|won't|it's|"
                          r"you're|I'm|I'd|that's|there's|let's|we're|they're)\b", re.I)


def sentences(text: str) -> list[str]:
    return [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def split_label(text: str) -> tuple[str, str]:
    first = text.split("\n", 1)[0].strip()
    m = LABEL_RE.match(first)
    if m and len(m.group("label").split()) <= 5:
        return m.group("label").strip(), text[m.end():].strip()
    return "", text.strip()


def stats(values: list[float]) -> dict:
    if not values:
        return {}
    return {
        "mean": round(statistics.fmean(values), 2),
        "std": round(statistics.pstdev(values), 2) if len(values) > 1 else 0.0,
        "min": round(min(values), 2),
        "max": round(max(values), 2),
    }


def is_specific(comment: str, quote: str) -> bool:
    if re.search(r"[\u201c\"][^\u201d\"]{3,}[\u201d\"]", comment):
        return True
    if re.search(r"\b[A-Z][a-z]+ et al\.|\b(?:19|20)\d{2}\b|\b\d+(?:\.\d+)?%", comment):
        return True
    # a content word borrowed from the anchored sentence
    q_words = {w.lower() for w in re.findall(r"[A-Za-z]{5,}", quote)}
    c_words = {w.lower() for w in re.findall(r"[A-Za-z]{5,}", comment)}
    return len(q_words & c_words) >= 2


def main(folder: str) -> None:
    source = Path(folder)
    files = sorted(source.glob("*.docx"))
    if not files:
        raise SystemExit(f"no .docx files in {source}")

    corpus = []
    comments = []
    endnotes = []
    for path in files:
        data = extract(path)
        reviewer = ""
        if data["comments"]:
            reviewer = data["comments"][0].get("author", "")
        doc_comments = []
        letter = ""
        for raw in data["comments"]:
            label, body = split_label(raw["text"])
            if not body.strip():
                continue
            record = {
                "doc": path.name,
                "reviewer": raw.get("author", reviewer),
                "label": label,
                "body": body,
                "quote": raw.get("quote", ""),
                "words": len(body.split()),
                "sentences": [len(s.split()) for s in sentences(body)],
            }
            comments.append(record)
            doc_comments.append(record)
        if data.get("endnote"):
            letter = data["endnote"]
        else:
            # These deliverables append the letter to the body, not word/endnotes.xml
            letter = body_letter(paragraphs(path))
        if letter:
            endnotes.append({
                "doc": path.name,
                "reviewer": reviewer,
                "text": letter,
                "words": len(letter.split()),
            })
        corpus.append({
            "doc": path.name,
            "reviewer": reviewer,
            "comments": doc_comments,
            "endnote_words": len(letter.split()) if letter else 0,
        })

    bodies = [c["body"] for c in comments]
    all_sentences = [n for c in comments for n in c["sentences"]]
    words = [c["words"] for c in comments]

    question = [c for c in comments if "?" in c["body"]]
    contractions = [c for c in comments if CONTRACTIONS.search(c["body"])]
    first_person = [c for c in comments if any(re.search(p, c["body"]) for p in FIRST_PERSON)]
    directives = [c for c in comments if any(d in c["body"].lower() for d in DIRECTIVES)]
    hedged = [c for c in comments if any(h in c["body"].lower() for h in HEDGES)]
    specific = [c for c in comments if is_specific(c["body"], c["quote"])]
    two_sentence = [c for c in comments if 2 <= len(sentences(c["body"])) <= 3]
    one_sentence = [c for c in comments if len(sentences(c["body"])) == 1]

    banned_hits = Counter()
    for body in bodies:
        low = body.lower()
        for term in BANNED:
            if term in low:
                banned_hits[term] += 1

    labels = Counter(c["label"].upper() for c in comments if c["label"])
    openers = Counter()
    for body in bodies:
        first = body.split()[0].strip(".,:;").lower() if body.split() else ""
        openers[first] += 1

    em_dash = sum(1 for b in bodies if "\u2014" in b)
    semicolon = sum(1 for b in bodies if ";" in b)
    colon = sum(1 for b in bodies if ":" in b)

    profile = {
        "documents": len(files),
        "reviewers": dict(Counter(c["reviewer"] for c in comments if c["reviewer"])),
        "comments": len(comments),
        "endnote_letters": len(endnotes),
        "comment_words": stats(words),
        "sentence_lengths": stats([float(n) for n in all_sentences]),
        "sentences_per_comment": stats([float(len(sentences(b))) for b in bodies]),
        "question_rate": round(len(question) / len(comments), 3),
        "contraction_rate": round(len(contractions) / len(comments), 3),
        "first_person_rate": round(len(first_person) / len(comments), 3),
        "directive_rate": round(len(directives) / len(comments), 3),
        "hedge_rate": round(len(hedged) / len(comments), 3),
        "specific_rate": round(len(specific) / len(comments), 3),
        "one_sentence_rate": round(len(one_sentence) / len(comments), 3),
        "two_or_three_sentence_rate": round(len(two_sentence) / len(comments), 3),
        "em_dash_comments": em_dash,
        "semicolon_comments": semicolon,
        "colon_comments": colon,
        "banned_hits": dict(banned_hits),
        "top_labels": dict(labels.most_common(15)),
        "top_openers": dict(openers.most_common(20)),
        "endnote_words": stats([float(e["words"]) for e in endnotes]),
        "examples": {
            "question": [c["body"] for c in question[:5]],
            "first_person": [c["body"] for c in first_person[:5]],
            "specific": [c["body"] for c in specific[:5]],
            "short": sorted(bodies, key=lambda b: len(b.split()))[:5],
            "long": sorted(bodies, key=lambda b: -len(b.split()))[:3],
        },
    }

    CORPUS_DIR.mkdir(exist_ok=True)
    (CORPUS_DIR / "voice_corpus.json").write_text(
        json.dumps({"documents": corpus, "comments": comments, "endnotes": endnotes},
                   indent=1, ensure_ascii=False),
        encoding="utf-8",
    )
    (CORPUS_DIR / "voice_profile.json").write_text(
        json.dumps(profile, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    write_report(profile, CORPUS_DIR / ".." / "docs" / "VOICE_PROFILE.md")
    print(json.dumps({k: v for k, v in profile.items() if k != "examples"},
                     indent=2, ensure_ascii=False))


def write_report(profile: dict, path: Path) -> None:
    p = profile
    lines = [
        "# Reviewer voice profile",
        "",
        f"Mined from {p['documents']} reviewed documents "
        f"({p['comments']} comments, {p['endnote_letters']} endnote letters).",
        "",
        "## Comment shape",
        "",
        f"- Words per comment: mean {p['comment_words'].get('mean')}, "
        f"std {p['comment_words'].get('std')}, range {p['comment_words'].get('min')}"
        f"\u2013{p['comment_words'].get('max')}.",
        f"- Sentence length: mean {p['sentence_lengths'].get('mean')}, "
        f"std {p['sentence_lengths'].get('std')}.",
        f"- One-sentence comments: {p['one_sentence_rate']:.0%}; "
        f"two or three: {p['two_or_three_sentence_rate']:.0%}.",
        "",
        "## Habits",
        "",
        f"- Questions: {p['question_rate']:.0%} of comments.",
        f"- Contractions: {p['contraction_rate']:.0%}.",
        f"- First person (I / I'd / my): {p['first_person_rate']:.0%}.",
        f"- Direct instructions (try, consider, make sure): {p['directive_rate']:.0%}.",
        f"- Hedges (a bit, maybe, seems): {p['hedge_rate']:.0%}.",
        f"- Specific reference to the student's text: {p['specific_rate']:.0%}.",
        f"- Em dashes: {p['em_dash_comments']}; semicolons: {p['semicolon_comments']}; "
        f"colons: {p['colon_comments']}.",
        "",
        "## Labels in use",
        "",
    ]
    for label, count in p["top_labels"].items():
        lines.append(f"- {label}: {count}")
    lines += ["", "## Common first words", ""]
    lines += [f"- {word}: {count}" for word, count in p["top_openers"].items()]
    lines += ["", "## LLM vocabulary found in the corpus", ""]
    if p["banned_hits"]:
        lines += [f"- {term}: {count}" for term, count in p["banned_hits"].items()]
    else:
        lines.append("- none")
    lines += ["", "## Examples", ""]
    for name, examples in p["examples"].items():
        lines.append(f"### {name}")
        lines += [f"- {e}" for e in examples]
        lines.append("")
    path.parent.mkdir(exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\shashank\Downloads\Doc examples")
