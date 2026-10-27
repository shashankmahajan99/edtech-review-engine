"""Create a text-only local alias from installed Qwen language weights.

Preserve the official template, renderer, parser and license. Omit only the
second FROM (vision projector). Ollama reuses the downloaded language blob.
"""
import argparse
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--source', default='qwen3.5:9b')
parser.add_argument('--name', default='thinkingstorm-qwen3.5:9b')
args = parser.parse_args()
runtime = ROOT / 'output/local-model/ollama/ollama.exe'
recipe = subprocess.check_output([str(runtime), 'show', args.source, '--modelfile'], text=True, encoding='utf-8')
lines, count = [], 0
for line in recipe.splitlines():
    if line.startswith('FROM '):
        count += 1
        if count > 1:
            continue
    lines.append(line)
if count == 0:
    raise RuntimeError('Official model recipe did not contain language weights.')
path = ROOT / 'output/local-model/TextReviewer.Modelfile'
path.write_text('# Text-only serving alias; vision projector omitted. Language weights unchanged.\n' + '\n'.join(lines) + '\n', encoding='utf-8')
subprocess.run([str(runtime), 'create', args.name, '-f', str(path)], check=True)
