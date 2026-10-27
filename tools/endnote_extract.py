"""Extract endnote letters that reviewers append to the document body.

These deliverables do not use word/endnotes.xml; the letter is the closing
section: praise, then "There are a few areas to focus on...", then next steps,
then a sign-off ("Best wishes, Mehak K." / "Regards, Mohini.").  Some are
followed by a formatting appendix, so the signature is located first and the
start is found by walking backwards.
"""
from __future__ import annotations

import re
import zipfile
from pathlib import Path

from lxml import etree

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SIGNATURE = re.compile(
    r"^(?:best wishes|best regards|regards|sincerely|warm regards|all the best)"
    r"[,.]?\s*$|^(?:best wishes|best regards|regards|sincerely|warm regards)[,.]\s*\S+",
    re.I,
)

START = re.compile(
    r"^(?:you have done (?:a )?(?:good|great|nice|fine|solid|decent|pretty) (?:job|work)|"
    r"you have (?:a )?(?:good|great|strong|solid) (?:start|draft)|"
    r"thank you for submitting|dear\s|(?:hi|hello)\s+[A-Za-z][A-Za-z'\u2019-]*[,!]?\s*$|"
    r"there are (?:a few|some) (?:areas|things|suggestions)|"
    r"you have written|your draft|you have a good start)",
    re.I,
)


def paragraphs(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"))
    out = []
    for p in root.iter(f"{W}p"):
        text = " ".join("".join(p.itertext()).split())
        if text:
            out.append(text)
    return out


def body_letter(paras: list[str]) -> str:
    sig = None
    for i in range(len(paras) - 1, -1, -1):
        if SIGNATURE.match(paras[i]):
            sig = i
            break
    if sig is None:
        return ""
    start = None
    hits = [i for i in range(max(0, sig - 45), sig) if START.match(paras[i])]
    if hits:
        start = min(hits)
    if start is None:
        return ""
    # include the name line after the signature when present
    end = min(len(paras), sig + 2)
    return "\n\n".join(paras[start:end]).strip()


if __name__ == "__main__":
    folder = Path(r"C:\Users\shashank\Downloads\Doc examples")
    for p in sorted(folder.glob("*.docx")):
        letter = body_letter(paragraphs(p))
        head = re.sub(r"\s+", " ", letter)[:110]
        print(f"{p.name[:55]:55s} {len(letter.split()):4d}w  {head}")
