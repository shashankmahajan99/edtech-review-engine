"""Rewrite an existing review's prose without regenerating its diagnoses or anchors."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.feedback_humanizer import LocalHumanizer
from engine.review.docmodel import load_document
from engine.review.endnote import Endnote
from engine.review.local_model import decode_comments
from engine.review.humanization import humanize_review
from engine.review.coverage import assess
from engine.review.writer import explode_runs, write_deliverable
from engine.review.validate import validate_deliverable

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('report', type=Path)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
payload = json.loads(args.report.read_text(encoding='utf-8-sig'))
source = Path(payload['input'])
if source.resolve() == args.output.resolve():
    raise ValueError('Never overwrite the source manuscript.')
model = load_document(str(source), academic_style=payload['style'])
if model.fingerprint != payload['fingerprint']:
    raise ValueError('Saved feedback belongs to a different manuscript.')
for paragraph in model.paragraphs:
    explode_runs(paragraph.element)
rows = [{'paragraph': c['paragraph'], 'quote': c['quote'], 'category': c['category'],
         'kind': c.get('kind', 'revision'), 'reason': c.get('diagnosis') or 'Previously reviewed exact passage in this manuscript.',
         'body': c['body']} for c in payload['comments']]
composed = decode_comments({'comments': rows}, model)
letter = Endnote(payload['endnote'], payload['endnote_domains'],
                 len(' '.join(payload['endnote']).split()), payload.get('endnote_evidence', []))
rewriter = LocalHumanizer()
with rewriter.session():
    revised, letter, audit, warnings = humanize_review(model, composed, letter, rewriter)
quality = assess(model, revised, letter)
quality['messages'].extend(warnings)
quality['needs_review'] = quality['needs_review'] or bool(warnings)
generation = {**payload.get('generation', {}), 'humanization': audit}
quality['generation'] = generation
args.output.parent.mkdir(parents=True, exist_ok=True)
written = write_deliverable(model, revised, letter.paragraphs, str(args.output),
                            reviewer_name=payload['reviewer'], reviewer_initials='RB')
validation = validate_deliverable(str(args.output), model,
    [(cid, item.finding.quote) for cid, (item, _) in zip(written.comment_ids, revised)],
    [body for _, body in revised], letter.paragraphs, reviewer_name=payload['reviewer'])
if not validation.ok:
    args.output.unlink(missing_ok=True)
    raise ValueError('; '.join(validation.errors))
comparison = {'comments': [{'before': before, 'after': after} for (_, before), (_, after) in zip(composed, revised)],
              'letter': [{'before': before, 'after': after} for before, after in zip(payload['endnote'], letter.paragraphs)]}
for comment, (_, body) in zip(payload['comments'], revised):
    comment['body'] = body
payload.update(output=str(args.output), endnote=letter.paragraphs, generation=generation,
               review_quality=quality, validation={'ok': True, 'errors': [], 'warnings': validation.warnings},
               humanization_comparison=comparison)
args.output.with_suffix('.review.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf8')
print(json.dumps({'output': str(args.output), 'humanization': audit, 'quality': quality}, indent=2))
