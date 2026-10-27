"""Save an existing model review as a manuscript-bound checkpoint for re-audit."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.review.docmodel import load_document
from engine.review.local_model import configuration, decode_comments

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('manuscript', type=Path, help='cleaned manuscript used for the original model run')
parser.add_argument('review', type=Path, help='the actual model review JSON trace')
parser.add_argument('--out', type=Path, required=True)
parser.add_argument('--config', type=Path, required=True)
args = parser.parse_args()
import os
os.environ['TS_LOCAL_CONFIG'] = str(args.config.resolve())
model = load_document(str(args.manuscript))
review = json.loads(args.review.read_text(encoding='utf8'))
decode_comments(review, model)
args.out.parent.mkdir(parents=True, exist_ok=True)
args.out.write_text(json.dumps({'fingerprint': model.fingerprint, 'model': configuration()['model'],
                                'review': review, 'source_trace': str(args.review.resolve())},
                               indent=2, ensure_ascii=False), encoding='utf8')
print('Saved checkpoint for ' + model.fingerprint[:16])
