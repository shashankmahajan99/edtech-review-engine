"""Extract native Word comments + endnotes from a .docx for style analysis.

Usage: python tools/extract_review.py <file.docx> [--json]

Prints, for every comment: id, anchored quote, full comment text, and author.
Then prints the endnote body. Read-only; nothing is modified.
"""
from __future__ import annotations

import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def _text(el) -> str:
    return "".join(t.text or "" for t in el.iter(f"{W}t"))


def _paras_text(parent) -> str:
    out = []
    for p in parent.iter(f"{W}p"):
        s = _text(p).strip()
        if s:
            out.append(s)
    return "\n".join(out)


def extract(path: Path) -> dict:
    z = zipfile.ZipFile(path)
    names = set(z.namelist())
    doc = ET.fromstring(z.read("word/document.xml"))

    # anchor text per comment id: walk every element in document order so that
    # anchors nested inside hyperlinks / smartTags / tables are captured too.
    anchored: dict[str, str] = {}
    open_ids: list[str] = []
    for el in doc.iter():
        if el.tag == f"{W}commentRangeStart":
            open_ids.append(el.get(f"{W}id"))
            anchored.setdefault(el.get(f"{W}id"), "")
        elif el.tag == f"{W}commentRangeEnd":
            cid = el.get(f"{W}id")
            if cid in open_ids:
                open_ids.remove(cid)
        elif el.tag == f"{W}t" and open_ids:
            for cid in open_ids:
                anchored[cid] = anchored.get(cid, "") + (el.text or "")

    comments = []
    if "word/comments.xml" in names:
        croot = ET.fromstring(z.read("word/comments.xml"))
        for c in croot.findall(f"{W}comment"):
            cid = c.get(f"{W}id")
            comments.append(
                {
                    "id": cid,
                    "author": c.get(f"{W}author"),
                    "initials": c.get(f"{W}initials"),
                    "quote": anchored.get(cid, ""),
                    "text": _paras_text(c),
                }
            )

    endnote = ""
    if "word/endnotes.xml" in names:
        eroot = ET.fromstring(z.read("word/endnotes.xml"))
        for en in eroot.findall(f"{W}endnote"):
            if en.get(f"{W}id") == "1":
                endnote = _paras_text(en)

    return {
        "file": str(path),
        "size": path.stat().st_size,
        "comment_count": len(comments),
        "comments": comments,
        "endnote": endnote,
        "parts": sorted(n for n in names if "comment" in n or "endnote" in n),
    }


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        return
    data = extract(Path(sys.argv[1]))
    if "--json" in sys.argv:
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    print(f"FILE: {data['file']}  ({data['size']:,} bytes, {data['comment_count']} comments)")
    print(f"PARTS: {', '.join(data['parts']) or '(none)'}")
    print("=" * 78)
    for c in data["comments"]:
        print(f"\n[{c['id']}] author={c['author']!r} initials={c['initials']!r}")
        print(f"  QUOTE    : {c['quote'][:300]!r}")
        print(f"  COMMENT  : {c['text']}")
    print("\n" + "=" * 78)
    print("ENDNOTE 1:\n" + (data["endnote"] or "(none)"))


if __name__ == "__main__":
    main()
