"""Review a DOCX using the configured local model, preserving the source."""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.review.pipeline import review_document

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('--out', type=Path, default=ROOT / 'output/local-model/reviews')
parser.add_argument('--config', type=Path, help='test a candidate configuration before deployment')
parser.add_argument('--checkpoint', type=Path, help='resume a matching model/manuscript checkpoint and recheck its feedback')
args = parser.parse_args()
if args.config:
    os.environ['TS_LOCAL_CONFIG'] = str(args.config.resolve())
args.out.mkdir(parents=True, exist_ok=True)
clean = args.out / 'inputs' / args.source.name
clean.parent.mkdir(parents=True, exist_ok=True)
# Cleanup is only needed for examples already reviewed. Ordinary drafts can be
# copied directly after native comment stripping and previous-letter removal.
from tools.strip_comments import strip
from engine.review.source_material import remove_previous_letter
strip(args.source, clean)
without_letter = clean.with_name(clean.stem + '.student.docx')
if remove_previous_letter(clean, without_letter)['removed']:
    without_letter.replace(clean)
result = review_document(clean, args.out, overwrite=True, backend='local', local_checkpoint=args.checkpoint)
print(json.dumps({'output': result.output_path, 'report': result.report_path,
                  'comments': len(result.comments), 'quality': result.quality,
                  'seconds': result.elapsed_seconds}, indent=2))
