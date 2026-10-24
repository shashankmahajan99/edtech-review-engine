"""Build the reviewer style corpus from genuine human-reviewed deliverables.

Reads the three reference deliverables (Janeen, Andrea, Kiran) and emits:
  style_corpus/exemplars.json   structured comments + endnotes per document
  style_corpus/exemplar_stats.json aggregate voice statistics

These files are the ground truth the deterministic composer is calibrated
against; no external services are involved.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.extract_review import extract  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "style_corpus"

EXEMPLARS = [
    ("janeen", Path(r"C:\Users\shashank\Downloads\janeen_REV_BY_TS_RaunakB_243347_1.docx")),
    ("andrea", Path(r"C:\Users\shashank\Downloads\andrea goblet.docx")),
    ("kiran", Path(r"C:\Users\shashank\Downloads\kiran mitra.docx")),
]

CATEGORY_RE = re.compile(
    r"^(?P<cats>[A-Z][A-Z&/\- ]{3,60}?)\s+(?=[A-Z][a-z]|\")"
)


def split_category(text: str) -> tuple[str, str]:
    """Split an ALL-CAPS leading category label off a comment body."""
    first = text.split("\n", 1)[0]
    m = CATEGORY_RE.match(first)
    if m:
        cats = m.group("cats").strip()
        # Require the label to be plausible (>=2 words or a known single word)
        if len(cats.split()) >= 1 and len(cats) >= 4:
            body = text[m.end():].lstrip()
            return cats, body
    return "", text


def sent_lengths(text: str) -> list[int]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [len(p.split()) for p in parts if p.strip()]


def main() -> None:
    CORPUS.mkdir(exist_ok=True)
    docs = []
    all_comments = []
    for name, path in EXEMPLARS:
        data = extract(path)
        for c in data["comments"]:
            label, body = split_category(c["text"])
            c["label"] = label
            c["body"] = body
            c["words"] = len(c["text"].split())
            c["quote_words"] = len(c["quote"].split())
            c["asks_question"] = "?" in c["text"]
            c["doc"] = name
            all_comments.append(c)
        end = data["endnote"]
        doms = re.findall(r"^([A-Z][^:\n]{3,70}):", end, flags=re.MULTILINE)
        docs.append(
            {
                "name": name,
                "source": str(path),
                "comment_count": len(data["comments"]),
                "endnote": end,
                "endnote_words": len(end.split()),
                "endnote_domains": doms,
            }
        )

    labels = [c["label"] for c in all_comments if c["label"]]
    stats = {
        "documents": len(docs),
        "comments": len(all_comments),
        "comments_per_doc": [d["comment_count"] for d in docs],
        "labelled_ratio": round(len(labels) / len(all_comments), 3),
        "categories": sorted({part for lab in labels for part in re.split(r"\s+AND\s+", lab)}),
        "words_per_comment": {
            "min": min(c["words"] for c in all_comments),
            "max": max(c["words"] for c in all_comments),
            "mean": round(sum(c["words"] for c in all_comments) / len(all_comments), 1),
        },
        "questions_ratio": round(
            sum(1 for c in all_comments if c["asks_question"]) / len(all_comments), 3
        ),
        "endnote_words": [d["endnote_words"] for d in docs],
        "endnote_domains": [d["endnote_domains"] for d in docs],
    }

    (CORPUS / "exemplars.json").write_text(
        json.dumps({"documents": docs, "comments": all_comments}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (CORPUS / "exemplar_stats.json").write_text(
        json.dumps(stats, indent=2), encoding="utf-8"
    )
    print(json.dumps(stats, indent=2))
    for d in docs:
        print(f"\n{d['name']}: {d['comment_count']} comments, endnote {d['endnote_words']}w, domains={d['endnote_domains']}")


if __name__ == "__main__":
    main()
