"""Build a private local retrieval index from reviewed DOCX examples (read-only)."""
from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from engine.review.docmodel import load_document
from engine.review.source_material import previous_letter_start
from portal.feedback_extract import W, LABEL, comment_text, extract_original_feedback
from tools.extract_review import extract


def build(source: Path, destination: Path):
    rows, documents = [], 0
    for path in sorted(source.glob('*.docx')):
        if path.name.startswith('~$'):
            continue
        model = load_document(str(path))
        letter_start = previous_letter_start(model.paragraphs)
        prose = [p.normalized for p in model.paragraphs if p.region == 'body'
                 and (letter_start is None or p.index < letter_start) and len(p.words) >= 40]
        probe = max(prose, key=len, default='')[:240]
        probe = re.sub(r'\s+', ' ', probe).strip()
        extracted = extract(path)
        letter = extract_original_feedback(path.read_bytes(), path.name)['endnote_text']
        with zipfile.ZipFile(path) as archive:
            if 'word/comments.xml' not in archive.namelist():
                continue
            xml = ET.fromstring(archive.read('word/comments.xml'))
        nodes = {node.get(W + 'id'): node for node in xml.findall(W + 'comment')}
        documents += 1
        first = True
        for entry in extracted['comments']:
            node = nodes[entry['id']]
            links = [''.join(t.text or '' for t in link.iter(W + 't')).strip()
                     for link in node.iter(W + 'hyperlink')]
            label_text = links[0] if links else entry['text']
            label = re.match(r'^\s*(' + LABEL + r')\b', label_text, re.I)
            category = label.group(1).upper() if label else label_text.split('\n')[0].split(':')[0].upper()
            feedback = comment_text(copy.deepcopy(node))
            if not feedback or not entry['quote'].strip():
                continue
            rows.append({'source': path.name, 'manuscript_probe': probe,
                         'category': category, 'quote': entry['quote'], 'feedback': feedback,
                         'letter': letter if first else ''})
            first = False
    if not rows:
        raise ValueError('No anchored human comments found.')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({'documents': documents, 'anchored_examples': len(rows), 'index': str(destination)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('--out', type=Path, default=ROOT / 'output/local-model/examples.json')
    args = parser.parse_args()
    build(args.source, args.out)
