"""Clever is now detector-only; feedback humanization runs locally."""
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_detector_widget_boundaries_and_lifecycle():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is unavailable')
    script = r'''
const assert = require('node:assert/strict');
const {normalizeUrl, mountDetector} = require('./portal/static/clever-widget.js');
const valid = 'https://widgets.cleverhumanizer.ai/embed/' + 'a'.repeat(32);
assert.equal(normalizeUrl(valid), valid + '?theme=light');
assert.equal(normalizeUrl(valid + '?theme=dark'), valid + '?theme=dark');
for (const bad of [valid + '&x=1', valid + '?theme=light&text=private', valid + '#x',
  valid.replace('https:', 'http:'), valid.replace('.ai/', '.ai.evil/'),
  valid.replace('.ai/', '.ai:443/'), valid.replace('widgets.', 'user@widgets.'),
  valid.replace('/embed/', '/x/../embed/'), '<iframe src="' + valid + '">',
  'javascript:alert(1)', valid + '?theme=unknown', valid + '/']) {
  assert.throws(() => normalizeUrl(bad), undefined, bad);
}
class Element {
  constructor() { this.value=''; this.textContent=''; this.handlers={}; this.children=[]; this.attrs={}; this.dataset={}; }
  addEventListener(name, callback) { this.handlers[name] = callback; }
  setAttribute(name, value) { this.attrs[name] = value; }
  replaceChildren(...children) { this.children = children; }
  async emit(name='click') { await this.handlers[name](); }
}
const nodes = {
  cleverDetectorFrame: new Element(),
  cleverDetectorStatus: new Element(),
  cleverDetectorLoad: new Element(),
  cleverDetectorClose: new Element(),
};
nodes.cleverDetectorFrame.dataset.widgetUrl = valid;
let created = 0;
mountDetector({document: {getElementById: id => nodes[id], createElement: () => { created++; return new Element(); }}});
assert.equal(created, 0);
nodes.cleverDetectorLoad.emit();
assert.equal(created, 1);
const frame = nodes.cleverDetectorFrame.children[0];
assert.equal(frame.src, valid + '?theme=light');
assert.ok(!frame.attrs.sandbox.includes('top-navigation'));
assert.equal(frame.attrs.allow, 'clipboard-write');
assert.match(nodes.cleverDetectorStatus.textContent, /Detector opened/);
nodes.cleverDetectorClose.emit();
assert.equal(nodes.cleverDetectorFrame.children.length, 0);
assert.match(nodes.cleverDetectorStatus.textContent, /Detector closed/);
''';
    result = subprocess.run([node, '-e', script], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
