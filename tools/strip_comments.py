"""Create a clean (uncommented) copy of a reviewed .docx.

Removes every comment part, anchor, reference run and related relationship so
the result behaves like a fresh student submission.  Used to build test
fixtures from the reviewer's exemplar deliverables.
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"
CT = "{http://schemas.openxmlformats.org/package/2006/content-types}"

DROP_PARTS = {
    "word/comments.xml",
    "word/commentsExtended.xml",
    "word/commentsExtensible.xml",
    "word/commentsIds.xml",
    "word/_rels/comments.xml.rels",
}


def strip(src: Path, dst: Path) -> None:
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        doc = etree.fromstring(z.read("word/document.xml"))
        rels = etree.fromstring(z.read("word/_rels/document.xml.rels"))
        ctypes = etree.fromstring(z.read("[Content_Types].xml"))

        for el in list(doc.iter(f"{W}commentRangeStart")) + list(doc.iter(f"{W}commentRangeEnd")):
            el.getparent().remove(el)
        for p in doc.iter(f"{W}p"):
            for run in list(p.findall(f"{W}r")):
                if run.find(f"{W}commentReference") is not None:
                    p.remove(run)

        for rel in list(rels.findall(f"{PKG}Relationship")):
            target = (rel.get("Target") or "").split("/")[-1]
            if target.startswith("comments"):
                rels.remove(rel)
        for over in list(ctypes.findall(f"{CT}Override")):
            if over.get("PartName", "").startswith("/word/comments"):
                ctypes.remove(over)

        dst.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as out:
            for name in names:
                if name in DROP_PARTS:
                    continue
                if name == "word/document.xml":
                    data = etree.tostring(doc, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif name == "word/_rels/document.xml.rels":
                    data = etree.tostring(rels, xml_declaration=True, encoding="UTF-8", standalone=True)
                elif name == "[Content_Types].xml":
                    data = etree.tostring(ctypes, xml_declaration=True, encoding="UTF-8", standalone=True)
                else:
                    data = z.read(name)
                out.writestr(name, data)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(__doc__)
        raise SystemExit(1)
    strip(Path(sys.argv[1]), Path(sys.argv[2]))
    print(f"wrote {sys.argv[2]}")
