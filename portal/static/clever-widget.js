/* Clever AI Detector only. Feedback humanization now runs locally. */
((root) => {
  'use strict';
  function normalizeUrl(value) {
    // Match the whole input before URL parsing can normalize away unsafe syntax.
    const match = /^https:\/\/widgets\.cleverhumanizer\.ai\/embed\/([a-f0-9]{32})(?:\?theme=(light|dark|auto))?$/i.exec(String(value).trim());
    if (!match) throw new Error('Use the iframe src URL from your own Clever widget, not the full embed code.');
    return `https://widgets.cleverhumanizer.ai/embed/${match[1].toLowerCase()}?theme=${(match[2] || 'light').toLowerCase()}`;
  }
  function feedbackText() {
    // Kept for callers that still ask; the local humanizer no longer copies feedback here.
    return '';
  }
  function createFrame(doc, url, title) {
    const frame = doc.createElement('iframe');
    frame.title = title;
    frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
    frame.setAttribute('allow', 'clipboard-write');
    frame.referrerPolicy = 'origin';
    frame.src = normalizeUrl(url);
    return frame;
  }
  function mountDetector({document: doc}) {
    const host = doc.getElementById('cleverDetectorFrame');
    const status = doc.getElementById('cleverDetectorStatus');
    doc.getElementById('cleverDetectorLoad').addEventListener('click', () => {
      try {
        host.replaceChildren(createFrame(doc, host.dataset.widgetUrl, 'Clever AI Detector — feedback checker'));
        status.textContent = 'Detector opened. Paste your feedback into the widget to check it. If blocked, allow this website in your Clever widget settings.';
      } catch (error) { status.textContent = error.message; }
    });
    doc.getElementById('cleverDetectorClose').addEventListener('click', () => {
      host.replaceChildren(); status.textContent = 'Detector closed. Nothing is sent automatically.';
    });
  }
  function mount() {
    // The Clever humanizer panel was removed; local Turnitout runs in the pipeline.
    return {clear() {}, setBusy() {}};
  }
  const api = {normalizeUrl, feedbackText, mount, mountDetector};
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.CleverWidget = api;
})(typeof window === 'undefined' ? globalThis : window);
