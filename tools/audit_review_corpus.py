"""Replay reviewed examples through the offline pipeline without editing sources.

Usage: python tools/audit_review_corpus.py SOURCE_FOLDER --out scratch/corpus-audit

Copies lose existing comments and the recognized reviewer letter/appendix before
reviewing. This audits deliverable integrity and feedback provenance, not an
authorship detector. Do not treat a passing result as a detector score.
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import zipfile
from html import escape
from pathlib import Path

from lxml import etree

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engine.review.docmodel import load_document, w
from engine.review.pipeline import review_document
from tools.audit_native import audit
from tools.endnote_extract import body_letter
from tools.extract_review import extract
from tools.strip_comments import strip


def prepare(source: Path, target: Path) -> bool:
    if source.resolve() == target.resolve():
        raise ValueError("corpus sources must never be overwritten")
    strip(source, target)
    # Exercise the same letter isolation as Studio, including its greeting.
    from engine.review.source_material import remove_previous_letter
    cleaned = target.with_name(target.stem + '.student.docx')
    if remove_previous_letter(target, cleaned)['removed']:
        cleaned.replace(target)
        return True
    model = load_document(str(target))
    texts = [p.normalized for p in model.paragraphs if p.normalized]
    letter = body_letter(texts)
    if not letter:
        raise ValueError("no reviewer letter recognized; refusing to analyse reviewer prose as student work")
    opening = letter.split("\n\n", 1)[0]
    start = next(p for p in model.paragraphs if p.normalized == opening)
    with zipfile.ZipFile(target) as archive:
        parts = {name: archive.read(name) for name in archive.namelist()}
    document = etree.fromstring(parts["word/document.xml"])
    # Use the model's XML element path, since table/textbox paragraphs are not
    # necessarily counted in the same order as top-level paragraphs.
    path = start.element.getroottree().getpath(start.element)
    matches = document.getroottree().xpath(path, namespaces={"w": w("p").split("}")[0][1:]})
    if len(matches) != 1 or matches[0].getparent().tag != w("body"):
        raise ValueError("reviewer letter does not start at a top-level paragraph")
    body = matches[0].getparent()
    for element in list(body)[body.index(matches[0]):]:
        if element.tag != w("sectPr"):
            body.remove(element)
    parts["word/document.xml"] = etree.tostring(document, xml_declaration=True, encoding="UTF-8", standalone=True)
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in parts.items():
            archive.writestr(name, content)
    target.write_bytes(data.getvalue())
    return True


def run(source: Path, output: Path) -> dict:
    files = sorted(source.glob("*.docx"))
    if not files:
        raise ValueError(f"no .docx examples in {source}")
    if output.resolve() == source.resolve() or source.resolve() in output.resolve().parents:
        raise ValueError("audit output must be outside the source corpus")
    rows = []
    comparisons = []
    for path in files:
        row = {"file": path.name}
        try:
            row["reference_comments"] = len(extract(path)["comments"])
            clean = output / "inputs" / path.name
            prepare(path, clean)
            result = review_document(clean, output / "reviews", overwrite=True)
            sidecar = json.loads(Path(result.report_path).read_text(encoding="utf-8"))
            delivered = {(c["rule"], c["paragraph"], c["quote"]) for c in result.comments}
            references = sidecar["endnote_evidence"]
            problems = audit(Path(result.output_path))
            if not references or any((e["rule"], e["paragraph"], e["quote"]) not in delivered for e in references):
                problems.append("endnote priority is not linked to a delivered comment")
            quality = result.quality
            reference = extract(path)['comments']
            row.update(ok=not problems, errors=problems, comments=len(result.comments),
                       endnote_words=result.validation.metrics["endnote_words"],
                       domains=sidecar["endnote_domains"], review_quality=quality,
                       reference_comment_words_mean=round(sum(len(c['text'].split()) for c in reference) / max(1, len(reference)), 1),
                       comment_words_mean=round(sum(len(c['body'].split()) for c in result.comments) / max(1, len(result.comments)), 1),
                       student_words=result.model.word_count)
            def cards(comments, generated=False):
                return ''.join('<article><blockquote>' + escape(c['quote']) + '</blockquote><p>' +
                               escape(c['body'] if generated else c['text']) + '</p></article>' for c in comments)
            reference_letter = body_letter([p.normalized for p in load_document(str(path)).paragraphs if p.text.strip()])
            comparisons.append('<section><h2>' + escape(path.name) + '</h2><p>' +
                               escape(' | '.join(quality['messages']) or 'Automated coverage and depth targets met; editorial accuracy still requires assessment.') +
                               '</p><div class="columns"><div><h3>Reviewer example (' + str(len(reference)) + ' comments)</h3>' +
                               cards(reference) + '<h3>Reference closing note</h3><pre>' + escape(reference_letter) +
                               '</pre></div><div><h3>Generated (' + str(len(result.comments)) + ' comments)</h3>' +
                               cards(result.comments, True) + '<h3>Generated closing note</h3><pre>' +
                               escape('\n\n'.join(result.endnote)) + '</pre></div></div></section>')
        except Exception as exc:
            row.update(ok=False, errors=[f"{type(exc).__name__}: {exc}"])
        rows.append(row)
    measured = [r for r in rows if 'review_quality' in r]
    report = {"scope": "Native Word integrity and provenance are release checks. Coverage and depth are measured proxies, not a claim of human-level editorial accuracy or a detector score.",
              "documents": len(rows), "passed": sum(r["ok"] for r in rows),
              "reference_comments": sum(r.get("reference_comments", 0) for r in rows),
              "generated_comments": sum(r.get('comments', 0) for r in rows),
              "coverage_and_depth_met": sum(not r['review_quality']['needs_review'] for r in measured),
              "needs_editorial_review": sum(r['review_quality']['needs_review'] for r in measured),
              "results": rows}
    output.mkdir(parents=True, exist_ok=True)
    (output / "audit.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (output / 'comparison.html').write_text('<!doctype html><meta charset="utf-8"><title>Reviewer corpus comparison</title>'
        '<style>body{font:16px/1.6 system-ui;margin:32px;background:#f5f5fa;color:#252239}h1,h2{line-height:1.3}'
        '.columns{display:grid;grid-template-columns:1fr 1fr;gap:24px}section{margin:48px 0;border-top:2px solid #aaa;padding-top:20px}'
        'article,pre{padding:18px;background:white;border:1px solid #ddd;border-radius:8px}article{margin:14px 0}'
        'blockquote{margin:0;color:#625777;border-left:3px solid #aaa;padding-left:12px}pre{white-space:pre-wrap;font:inherit}'
        '@media(max-width:800px){.columns{grid-template-columns:1fr}}</style><h1>Reference and generated reviews</h1>'
        '<p>Columns are separate reviews, not matched comments. Counts, depth and Word structure are measured; '
        'these checks do not establish semantic accuracy. Original example files were not modified.</p>' +
        ''.join(comparisons), encoding='utf-8')
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "scratch" / "corpus-audit")
    args = parser.parse_args()
    result = run(args.source, args.out)
    print(json.dumps({k: v for k, v in result.items() if k != "results"}, indent=2))
    for row in result["results"]:
        if not row["ok"]:
            print(row["file"], row["errors"])
    raise SystemExit(0 if result["passed"] == result["documents"] else 1)
