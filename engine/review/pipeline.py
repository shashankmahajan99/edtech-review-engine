"""End-to-end ThinkingStorm review pipeline (local model or offline rules).

    input.docx -> analyse -> select -> compose -> anchor -> validate -> deliver

Any failure in the release gate aborts the deliverable instead of shipping a
half-correct file.  A JSON sidecar records exactly what was produced and why.
"""
from __future__ import annotations

import json
import os
import time
from contextlib import nullcontext
from dataclasses import dataclass, field
from pathlib import Path

from .analysis import AnalysisResult, analyze
from . import diagnostics
from .docmodel import DocumentModel, load_document
from .endnote import Endnote, compose_endnote
from .selection import SelectedComment, select_comments
from .validate import ValidationReport, validate_deliverable
from .persona import CompositionError, compose_all
from .writer import can_anchor, explode_runs, normalize_span, write_deliverable
from .progress import emit_progress


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
    quality: dict = field(default_factory=dict)
    generation: dict = field(default_factory=dict)


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
    backend: str | None = None,
    local_checkpoint: str | Path | None = None,
    feedback_rewriter=None,
    progress=None,
) -> ReviewResult:
    started = time.time()
    src = Path(input_path)
    if not src.exists():
        raise PipelineError(f"input not found: {src}")
    if src.suffix.lower() != ".docx":
        raise PipelineError(f"only .docx manuscripts are supported here: {src.name}")

    model = load_document(str(src), academic_style=academic_style)
    emit_progress(progress, 'reviewing')
    model.meta['requested_academic_style'] = academic_style
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
    chosen_backend = backend or os.environ.get('TS_REVIEW_BACKEND', 'rules')
    generation = {'backend': 'rules', 'detector_score': None}
    local_composed = None
    if chosen_backend == 'local':
        from .local_model import LocalReviewError, compose_local
        try:
            if local_checkpoint:
                local_composed, endnote, generation = compose_local(model, result, reviewer_name, student_name, checkpoint=local_checkpoint)
            else:
                local_composed, endnote, generation = compose_local(model, result, reviewer_name, student_name)
        except LocalReviewError as exc:
            raise PipelineError(str(exc)) from exc
        selected = [item for item, _ in local_composed]
    elif chosen_backend == 'rules':
        selected = select_comments(model, result, comprehensive=comprehensive)
    else:
        raise PipelineError(f'Unknown review backend: {chosen_backend}')

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
    if not selected:
        raise PipelineError(
            "no supported comments survived selection; a manual review is needed"
        )
    if local_composed is not None and dropped:
        raise PipelineError('Local review contained unanchorable comments; review was not delivered.')
    from .selection import RHETORICAL
    misplaced = [item for item in selected if item.category.split(' AND ')[0] in RHETORICAL
                 and item.finding.paragraph.region in {'references', 'reviewer_note'}]
    if misplaced:
        raise PipelineError('rhetorical feedback cannot be attached to source entries or previous reviewer material')

    try:
        if local_composed is not None:
            composed = local_composed
        else:
            composed = compose_all(model, selected, result.essay_type)
            endnote: Endnote = compose_endnote(model, result, reviewer_name=reviewer_name,
                                             student_name=student_name, composed=composed)
    except CompositionError as exc:
        raise PipelineError(f"feedback composition failed: {exc}") from exc
    humanizer_warnings = []
    from .humanization import feedback_piece_count
    emit_progress(progress, 'feedback_ready', total_passages=feedback_piece_count(composed, endnote) if feedback_rewriter is not None else 0,
                  completed_passages=0)
    if feedback_rewriter is not None:
        from .humanization import humanize_review
        try:
            with feedback_rewriter.session() if hasattr(feedback_rewriter, 'session') else nullcontext():
                composed, endnote, audit, humanizer_warnings = humanize_review(model, composed, endnote, feedback_rewriter, progress=progress)
            generation['humanization'] = audit
        except (RuntimeError, ValueError) as exc:
            raise PipelineError('Feedback humanization failed: ' + str(exc)) from exc
    from .coverage import assess
    quality = assess(model, composed, endnote)
    quality['messages'].extend(humanizer_warnings)
    quality['needs_review'] = quality['needs_review'] or bool(humanizer_warnings)
    quality['generation'] = generation

    out_dir = Path(output_dir) if output_dir else src.parent
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _output_name(src.stem)
    if not overwrite:
        out_path = _unique(out_path)

    emit_progress(progress, 'document')
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
    validation.warnings.extend(quality['messages'])

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
                "diagnosis": item.finding.facts.get('reason', ''),
                "kind": item.finding.facts.get('kind', 'revision'),
            }
            for i, (item, body) in enumerate(composed)
        ],
        "endnote": endnote.paragraphs,
        "endnote_domains": endnote.domains,
        "endnote_evidence": endnote.evidence,
        "review_quality": quality,
        "generation": generation,
        "editorial_status": "needs_review" if quality['needs_review'] else "automated_targets_met",
        "quality_scope": "Editorial and document integrity checks; no authorship-detector score is measured or inferred.",
        "validation": {
            "ok": validation.ok,
            "errors": validation.errors,
            "warnings": validation.warnings,
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

    emit_progress(progress, 'document_ready')

    return ReviewResult(
        input_path=str(src),
        output_path=str(out_path),
        report_path=str(report_path),
        comments=[
            {
                "id": str(i),
                "category": item.category if item.labelled else "",
                "rule": item.finding.rule_id,
                "diagnostic": diagnostics.for_rule(item.finding.rule_id),
                "paragraph": item.finding.paragraph.index,
                "quote": item.finding.quote,
                "body": body,
                "diagnosis": item.finding.facts.get('reason', ''),
                "kind": item.finding.facts.get('kind', 'revision'),
            }
            for i, (item, body) in enumerate(composed)
        ],
        endnote=endnote.paragraphs,
        analysis=result,
        validation=validation,
        elapsed_seconds=round(time.time() - started, 2),
        model=model,
        quality=quality,
        generation=generation,
    )
