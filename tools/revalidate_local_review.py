"""Rebuild a saved model review through the current formatter and Word gate.

No inference or feedback rewriting occurs. Useful after a deterministic formatter
fix, without regenerating an already audited review on a slow local model.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.review.coverage import assess
from engine.review.docmodel import load_document
from engine.review.local_model import decode_comments, decode_endnote
from engine.review.validate import validate_deliverable
from engine.review.writer import can_anchor, explode_runs, normalize_span, write_deliverable

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('report', type=Path)
parser.add_argument('letter', type=Path, help='actual model letter JSON trace')
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
payload = json.loads(args.report.read_text(encoding='utf-8-sig'))
source = Path(payload['input'])
if source.resolve() == args.output.resolve():
    raise ValueError('Never overwrite the manuscript source.')
model = load_document(str(source), academic_style=payload['style'])
if model.fingerprint != payload['fingerprint']:
    raise ValueError('The saved review belongs to a different manuscript.')
for paragraph in model.paragraphs:
    explode_runs(paragraph.element)
rows = [{'paragraph': c['paragraph'], 'quote': c['quote'], 'category': c['category'],
         'kind': c.get('kind', 'revision'), 'reason': c.get('diagnosis') or 'Previously audited model feedback on this exact passage.',
         'body': c['body']} for c in payload['comments']]
composed = decode_comments({'comments': rows}, model)
for item, _ in composed:
    f = item.finding
    f.start, f.end = normalize_span(f.paragraph.element, f.start, f.end)
    if not can_anchor(f.paragraph.element, f.start, f.end):
        raise ValueError('An approved comment cannot be anchored.')
student = payload['endnote'][0].removeprefix('Dear ').removesuffix(',')
reviewer = payload['reviewer']
letter = decode_endnote(json.loads(args.letter.read_text(encoding='utf8')), model, composed, reviewer, student)
args.output.parent.mkdir(parents=True, exist_ok=True)
quality = assess(model, composed, letter)
quality['generation'] = payload.get('generation', {})
written = write_deliverable(model, composed, letter.paragraphs, str(args.output),
                            reviewer_name=reviewer,
                            reviewer_initials=''.join(part[0] for part in reviewer.split())[:3])
validation = validate_deliverable(str(args.output), model,
    [(cid, item.finding.quote) for cid, (item, _) in zip(written.comment_ids, composed)],
    [body for _, body in composed], letter.paragraphs, reviewer_name=reviewer)
if not validation.ok:
    raise ValueError('; '.join(validation.errors))
payload.update(output=str(args.output), endnote=letter.paragraphs,
               endnote_domains=letter.domains, endnote_evidence=letter.evidence,
               review_quality=quality, format_revalidated_at=datetime.now(timezone.utc).isoformat(),
               validation={'ok': True, 'errors': [], 'warnings': validation.warnings,
                           'metrics': validation.metrics})
report = args.output.with_suffix('.review.json')
report.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf8')
print(json.dumps({'output': str(args.output), 'report': str(report), 'quality': quality}, indent=2))
