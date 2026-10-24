"""End-to-end ThinkingStorm review pipeline (offline, zero tokens).

    input.docx -> analyse -> select -> compose -> anchor -> validate -> deliver

Any failure in the release gate aborts the deliverable instead of shipping a
half-correct file.  A JSON sidecar records exactly what was produced and why.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .analysis import AnalysisResult, analyze
from .docmodel import DocumentModel, load_document
from .endnote import Endnote, compose_endnote
from .selection import SelectedComment, select_comments
from .validate import ValidationReport, validate_deliverable
from .persona import compose_all
from .writer import can_anchor, explode_runs, normalize_span, write_deliverable


class PipelineError(RuntimeError):
    """Raised when a manuscript cannot be reviewed safely."""


@dataclass
class ReviewResult:
    input_path: str
    output_path: str
    report_path: str
    comments: list[dict]
    endnote: list[str]
    analysis: AnalysisResult
    validation: ValidationReport
    elapsed_seconds: float
    model: DocumentModel = field(repr=False, default=None)


def _output_name(stem: str) -> str:
    return f"{stem}_commented.docx"


def _unique(path: Path) -> Path:
    if not path.exists():
        return path
    for i in range(2, 100):
        candidate = path.with_name(f"{path.stem}-{i}{path.suffix}")
        if not candidate.exists():
            return candidate
    raise PipelineError(f"cannot find a free filename for {path}")


def review_document(
    input_path: str | Path,
    output_dir: str | Path | None = None,
    reviewer_name: str = "Raunak Banga",
    reviewer_initials: str = "RB",
    student_name: str | None = None,
    academic_style: str = "auto",
    allow_existing_comments: bool = False,
    overwrite: bool = False,
    comprehensive: bool = True,
) -> ReviewResult:
    started = time.time()
    src = Path(input_path)
    if not src.exists():
        raise PipelineError(f"input not found: {src}")
    if src.suffix.lower() != ".docx":
        raise PipelineError(f"only .docx manuscripts are supported here: {src.name}")

    model = load_document(str(src), academic_style=academic_style)
    for paragraph in model.paragraphs:
        explode_runs(paragraph.element)
    if model.has_existing_comments and not allow_existing_comments:
        raise PipelineError(
            f"{src.name} already contains comments; pass allow_existing_comments=True "
            "to append a second review"
        )
    if model.word_count < 80:
        raise PipelineError(f"{src.name} is too short to review ({model.word_count} words)")

    result = analyze(model)
    selected = select_comments(model, result, comprehensive=comprehensive)

    # Only keep findings whose span can actually be anchored.
    paragraph_by_index = {p.index: p for p in model.paragraphs}
    anchorable: list[SelectedComment] = []
    for item in selected:
        para = paragraph_by_index.get(item.finding.paragraph.index)
        if para is None:
            continue
        start, end = normalize_span(para.element, item.finding.start, item.finding.end)
        if can_anchor(para.element, start, end):
            item.finding.start, item.finding.end = start, end
            anchorable.append(item)
    dropped = len(selected) - len(anchorable)
    if dropped > max(2, len(selected) // 4):
        raise PipelineError(f"{dropped} of {len(selected)} comments could not be anchored")
    selected = anchorable
    if model.word_count < 300:
        minimum = 3
    elif model.word_count < 600:
        minimum = 4
    else:
        minimum = 5
    if len(selected) < minimum:
        raise PipelineError(
            f"only {len(selected)} comments survived selection; refusing to ship"
        )

    composed = compose_all(model, selected, result.essay_type)
    endnote: Endnote = compose_endnote(model, result, reviewer_name=reviewer_name,
                                       student_name=student_name)

    out_dir = Path(output_dir) if output_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _output_name(src.stem)
    if not overwrite:
        out_path = _unique(out_path)

    written = write_deliverable(
        model=model,
        composed=composed,
        endnote_paragraphs=endnote.paragraphs,
        output_path=str(out_path),
        reviewer_name=reviewer_name,
        reviewer_initials=reviewer_initials,
    )

    expected = [(cid, item.finding.quote) for cid, (item, _body) in zip(written.comment_ids, composed)]
    bodies = [body for _item, body in composed]
    validation = validate_deliverable(
        str(out_path), model, expected, bodies, endnote.paragraphs,
        reviewer_name=reviewer_name,
    )

    report_path = out_path.with_suffix(".review.json")
    payload = {
        "input": str(src),
        "output": str(out_path),
        "fingerprint": model.fingerprint,
        "style": model.style,
        "essay_type": result.essay_type,
        "word_count": model.word_count,
        "reviewer": reviewer_name,
        "metrics": result.metrics,
        "findings": [
            {
                "rule": f.rule_id,
                "category": f.category,
                "paragraph": f.paragraph.index,
                "priority": f.priority,
                "quote": f.quote,
            }
            for f in result.findings
        ],
        "comments": [
            {
                "id": str(i),
                "category": item.category if item.labelled else "",
                "rule": item.finding.rule_id,
                "paragraph": item.finding.paragraph.index,
                "quote": item.finding.quote,
                "body": body,
            }
            for i, (item, body) in enumerate(composed)
        ],
        "endnote": endnote.paragraphs,
        "endnote_domains": endnote.domains,
        "validation": {
            "ok": validation.ok,
            "errors": validation.errors,
            "metrics": validation.metrics,
        },
        "elapsed_seconds": round(time.time() - started, 2),
    }
    report_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    if not validation.ok:
        try:
            out_path.unlink()
        except OSError:
            pass
        raise PipelineError(
            "validation failed: " + "; ".join(validation.errors[:6])
        )

    return ReviewResult(
        input_path=str(src),
        output_path=str(out_path),
        report_path=str(report_path),
        comments=[
            {
                "id": str(i),
                "category": item.category if item.labelled else "",
                "rule": item.finding.rule_id,
                "paragraph": item.finding.paragraph.index,
                "quote": item.finding.quote,
                "body": body,
            }
            for i, (item, body) in enumerate(composed)
        ],
        endnote=endnote.paragraphs,
        analysis=result,
        validation=validation,
        elapsed_seconds=round(time.time() - started, 2),
        model=model,
    )
