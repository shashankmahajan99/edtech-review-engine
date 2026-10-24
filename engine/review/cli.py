"""Command line interface for the ThinkingStorm review pipeline.

Examples
--------
    python -m engine.review.cli review draft.docx
    python -m engine.review.cli review draft.docx --out deliverables --style apa
    python -m engine.review.cli batch ./inbox --out ./outbox
    python -m engine.review.cli watch --inbox ./inbox --outbox ./outbox
    python -m engine.review.cli selftest --fixtures tests/fixtures
    python -m engine.review.cli dry-run draft.docx
    python -m engine.review.cli audit deliverable_commented.docx
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analysis import analyze
from .docmodel import load_document
from .pipeline import PipelineError, review_document
from .selection import select_comments
from .persona import compose_all


def _print_result(result) -> None:
    print(f"\nOK  {Path(result.input_path).name}")
    print(f"    deliverable : {result.output_path}")
    print(f"    report      : {result.report_path}")
    print(f"    comments    : {len(result.comments)}")
    print(f"    endnote     : {sum(len(p.split()) for p in result.endnote)} words")
    print(f"    elapsed     : {result.elapsed_seconds}s")
    for comment in result.comments:
        label = comment["category"] or "(note)"
        print(f"      - {label}: \"{comment['quote'][:70]}\"")
        print(f"        {comment['body']}")


def cmd_review(args: argparse.Namespace) -> int:
    try:
        result = review_document(
            args.file,
            output_dir=args.out,
            reviewer_name=args.reviewer,
            reviewer_initials=args.initials,
            student_name=args.student,
            academic_style=args.style,
            allow_existing_comments=args.allow_existing,
            overwrite=args.overwrite,
        )
    except PipelineError as exc:
        print(f"REJECTED: {exc}", file=sys.stderr)
        return 2
    _print_result(result)
    if args.json:
        print(json.dumps({"report": result.report_path, "validation": result.validation.metrics}, indent=2))
    return 0


def cmd_batch(args: argparse.Namespace) -> int:
    source = Path(args.directory)
    if not source.is_dir():
        print(f"not a directory: {source}", file=sys.stderr)
        return 2
    files = sorted(p for p in source.glob("*.docx") if not p.name.startswith("~$"))
    if not files:
        print("no .docx files found")
        return 0
    failures = 0
    for path in files:
        try:
            result = review_document(
                path, output_dir=args.out or source, reviewer_name=args.reviewer,
                reviewer_initials=args.initials, academic_style=args.style,
                allow_existing_comments=args.allow_existing, overwrite=args.overwrite,
            )
            print(f"OK   {path.name} -> {Path(result.output_path).name} "
                  f"({len(result.comments)} comments)")
        except PipelineError as exc:
            failures += 1
            print(f"FAIL {path.name}: {exc}", file=sys.stderr)
    print(f"\n{len(files) - failures}/{len(files)} reviewed")
    return 0 if failures == 0 else 1


def cmd_watch(args: argparse.Namespace) -> int:
    from .watch import run_watcher

    run_watcher(Path(args.inbox), Path(args.outbox), args.interval,
                args.reviewer, args.initials, args.style, once=args.once)
    return 0


def cmd_dry_run(args: argparse.Namespace) -> int:
    model = load_document(args.file, academic_style=args.style)
    result = analyze(model)
    selected = select_comments(model, result)
    composed = compose_all(model, selected, result.essay_type)
    print(f"{Path(args.file).name}: {model.word_count} words, style={model.style}, "
          f"type={result.essay_type}, blocks={len(result.blocks)}")
    print(f"findings={len(result.findings)} selected={len(selected)}")
    for item, body in composed:
        finding = item.finding
        print(f"  p{finding.paragraph.index:02d} [{item.category or '-':24s}] "
              f"pri {finding.priority:3d} {finding.rule_id}")
        print(f"      quote: {finding.quote[:100]!r}")
        print(f"      body : {body}")
    return 0


def cmd_selftest(args: argparse.Namespace) -> int:
    fixtures = Path(args.fixtures)
    files = sorted(fixtures.glob("*.docx"))
    if not files:
        print(f"no fixtures in {fixtures}", file=sys.stderr)
        return 2
    failures = 0
    for path in files:
        try:
            result = review_document(path, output_dir=args.out or (fixtures / "_out"),
                                     overwrite=True)
        except PipelineError as exc:
            failures += 1
            print(f"FAIL {path.name}: {exc}", file=sys.stderr)
            continue
        metrics = result.validation.metrics
        print(f"PASS {path.name}: {metrics.get('comments')} comments, "
              f"{metrics.get('endnote_words')} endnote words, "
              f"style={metrics.get('style', {}).get('burstiness_std')}")
    return 0 if failures == 0 else 1


def cmd_audit(args: argparse.Namespace) -> int:
    """Show the stylometric evidence for a finished deliverable."""
    import zipfile

    from lxml import etree

    from .style_guard import (
        banned_hits, burstiness, opener_ratio, repeated_ngram_ratio,
    )
    from .validate import W as W_TAG, _comment_body

    path = Path(args.file)
    if not path.exists():
        print(f"not found: {path}", file=sys.stderr)
        return 2
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        if "word/comments.xml" not in names or "word/endnotes.xml" not in names:
            print("no ThinkingStorm deliverable parts in this file", file=sys.stderr)
            return 2
        c_root = etree.fromstring(z.read("word/comments.xml"))
        e_root = etree.fromstring(z.read("word/endnotes.xml"))

    bodies = [_comment_body(c) for c in c_root.findall(f"{W_TAG}comment")]
    bodies = [b for b in bodies if b]
    endnote = ""
    for en in e_root.findall(f"{W_TAG}endnote"):
        if en.get(f"{W_TAG}id") == "1":
            endnote = " ".join(
                "".join(t.text or "" for t in p.iter(f"{W_TAG}t"))
                for p in en.findall(f"{W_TAG}p")
            ).strip()

    joined = " ".join(bodies)
    mean, std = burstiness(joined)
    en_mean, en_std = burstiness(endnote)
    hits = sorted({h for b in bodies + [endnote] for h in banned_hits(b)})
    lengths = [len(b.split()) for b in bodies]

    print(f"FILE       {path.name}")
    print(f"comments   {len(bodies)}")
    print(f"lengths    {lengths}")
    print(f"sentences  mean {mean:.1f} words | variance(std) {std:.2f}")
    print(f"5-grams    repeat ratio {repeated_ngram_ratio(bodies):.3f}")
    print(f"openers    variety {opener_ratio(bodies):.2f}")
    print(f"endnote    {len(endnote.split())} words | "
          f"mean {en_mean:.1f} | std {en_std:.2f}")
    print(f"banned     {hits or 'none'}")

    ok = True
    if len({round(length, 0) for length in lengths}) < 2 and len(bodies) >= 4:
        print("note       comment lengths cluster; add short/long variety")
    if len(bodies) >= 3 and std < 2.6:
        ok = False
        print("FAIL       sentence lengths too uniform for the human band")
    if hits:
        ok = False
        print("FAIL       banned AI phrasing present")
    print("RESULT     " + ("PASS" if ok else "REVIEW"))
    return 0 if ok else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine.review.cli",
        description="Deterministic ThinkingStorm review pipeline (offline, zero tokens)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--reviewer", default="Raunak Banga")
        p.add_argument("--initials", default="RB")
        p.add_argument("--style", default="auto", choices=["auto", "mla", "apa"])
        p.add_argument("--allow-existing", action="store_true",
                       help="append a review even if the file already has comments")

    review = sub.add_parser("review", help="review one .docx")
    review.add_argument("file")
    review.add_argument("--out", default=None)
    review.add_argument("--student", default=None)
    review.add_argument("--overwrite", action="store_true")
    review.add_argument("--json", action="store_true")
    common(review)
    review.set_defaults(func=cmd_review)

    batch = sub.add_parser("batch", help="review every .docx in a directory")
    batch.add_argument("directory")
    batch.add_argument("--out", default=None)
    batch.add_argument("--overwrite", action="store_true")
    common(batch)
    batch.set_defaults(func=cmd_batch)

    watch = sub.add_parser("watch", help="poll an inbox folder and review new files")
    watch.add_argument("--inbox", default="inbox")
    watch.add_argument("--outbox", default="outbox")
    watch.add_argument("--interval", type=int, default=10)
    watch.add_argument("--once", action="store_true")
    common(watch)
    watch.set_defaults(func=cmd_watch)

    dry = sub.add_parser("dry-run", help="show findings without writing a document")
    dry.add_argument("file")
    dry.add_argument("--style", default="auto", choices=["auto", "mla", "apa"])
    dry.set_defaults(func=cmd_dry_run)

    selftest = sub.add_parser("selftest", help="run the pipeline over sample fixtures")
    selftest.add_argument("--fixtures", default="tests/fixtures")
    selftest.add_argument("--out", default=None)
    selftest.set_defaults(func=cmd_selftest)

    audit = sub.add_parser("audit", help="show stylometric metrics for a deliverable")
    audit.add_argument("file")
    audit.set_defaults(func=cmd_audit)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
