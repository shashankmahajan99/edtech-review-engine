"""Audit a .docx for genuinely native Word comments and endnotes."""
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"


def audit(path: Path) -> list[str]:
    problems: list[str] = []
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        doc = etree.fromstring(z.read("word/document.xml"))

        body = doc.find(f"{W}body")
        children = list(body)
        sect_indexes = [i for i, child in enumerate(children) if child.tag == f"{W}sectPr"]
        if sect_indexes and sect_indexes[-1] != len(children) - 1:
            problems.append("w:sectPr is not the last body element")

        # comments
        starts = doc.findall(f".//{W}commentRangeStart")
        ends = doc.findall(f".//{W}commentRangeEnd")
        refs = doc.findall(f".//{W}commentReference")
        start_ids = [e.get(f"{W}id") for e in starts]
        end_ids = [e.get(f"{W}id") for e in ends]
        ref_ids = [e.get(f"{W}id") for e in refs]
        if sorted(start_ids) != sorted(end_ids):
            problems.append("commentRangeStart/End ids differ")
        if sorted(start_ids) != sorted(ref_ids):
            problems.append("comment range ids and commentReference ids differ")
        if "word/comments.xml" in names:
            comments = etree.fromstring(z.read("word/comments.xml"))
            cids = [c.get(f"{W}id") for c in comments.findall(f"{W}comment")]
            if sorted(cids) != sorted(start_ids):
                problems.append("comments.xml ids do not match document ranges")
            for c in comments.findall(f"{W}comment"):
                if not c.get(f"{W}author"):
                    problems.append(f"comment {c.get(f'{W}id')} has no author")
                if not "".join(c.itertext()).strip():
                    problems.append(f"comment {c.get(f'{W}id')} has no text")
        elif starts:
            problems.append("comment ranges exist but word/comments.xml is missing")

        # endnotes
        erefs = doc.findall(f".//{W}endnoteReference")
        if "word/endnotes.xml" in names:
            endnotes = etree.fromstring(z.read("word/endnotes.xml"))
            eids = [e.get(f"{W}id") for e in endnotes.findall(f"{W}endnote")]
            for ref in erefs:
                if ref.get(f"{W}id") not in eids:
                    problems.append(f"endnoteReference {ref.get(f'{W}id')} missing from endnotes.xml")
            for e in endnotes.findall(f"{W}endnote"):
                if e.get(f"{W}id") in {"-1", "0"}:
                    continue
                if e.find(f".//{W}endnoteRef") is None:
                    problems.append(f"endnote {e.get(f'{W}id')} lacks w:endnoteRef")
        elif erefs:
            problems.append("endnote references exist but word/endnotes.xml is missing")

        # relationships
        rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
        rel_ids = [r.get("Id") for r in rels]
        if len(rel_ids) != len(set(rel_ids)):
            problems.append("duplicate relationship ids")
        part_rels = [r for r in rels if (r.get("Type") or "").rsplit("/", 1)[-1] in {"comments", "endnotes"}]
        seen_types = [r.get("Type") for r in part_rels]
        if len(seen_types) != len(set(seen_types)):
            problems.append("duplicate comments/endnotes relationships (Word repair trigger)")
        targets = {r.get("Target") for r in rels}
        if "comments.xml" in names and "comments.xml" not in targets:
            problems.append("comments.xml not linked from document rels")
        if "endnotes.xml" in names and "endnotes.xml" not in targets:
            problems.append("endnotes.xml not linked from document rels")

        # content types
        types = etree.fromstring(z.read("[Content_Types].xml"))
        overrides = {o.get("PartName"): o.get("ContentType") for o in types}
        part_names = [o.get("PartName") for o in types.findall(f"{CT}Override")]
        if len(part_names) != len(set(part_names)):
            problems.append("duplicate content-type overrides")
        if "comments.xml" in names:
            ct = overrides.get("/word/comments.xml", "")
            if not ct.endswith("comments+xml"):
                problems.append(f"wrong content type for comments: {ct!r}")
        if "endnotes.xml" in names:
            ct = overrides.get("/word/endnotes.xml", "")
            if not ct.endswith("endnotes+xml"):
                problems.append(f"wrong content type for endnotes: {ct!r}")

        # no inline editorial notes left in the manuscript
        text = "".join(doc.itertext())
        if "Editorial Note" in text:
            problems.append("inline 'Editorial Note' text present in body")

    return problems


if __name__ == "__main__":
    targets = sys.argv[1:] or [
        "output/review_v2/janeen_raw_commented.docx",
        "output/review_v2/andrea_raw_commented.docx",
        "output/review_v2/kiran_raw_commented.docx",
    ]
    for target in targets:
        p = Path(target)
        if not p.exists():
            print(f"{target}: missing")
            continue
        issues = audit(p)
        status = "NATIVE OK" if not issues else "PROBLEMS: " + "; ".join(issues)
        print(f"{p.name}: {status}")
