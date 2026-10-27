# Clever manual widget in Studio

## Scope and evidence

User authorizes the manual widget and asks to automate its use. Official
https://cleverhumanizer.ai/api documents an interactive iframe issued to an
account for allowed sites, but no public text submission or result callback.
Implement preparation and loading, with explicit manual submission. Do not claim
automatic processing or modify generated Word downloads with unvalidated text.

## Design

Add an always available collapsed panel beneath the Studio grid. It explains the
manual workflow, links the official widget setup and privacy policy, and lets the
user supply the iframe src URL issued by Clever for this localhost origin.
Accept only HTTPS widgets.cleverhumanizer.ai/embed/<32 hexadecimal characters>,
with no credentials, port, fragment or query except theme=light|dark|auto.
Normalize theme to light. Do not accept script or iframe markup.

Loading requires an explicit button. No third-party frame or network request
occurs on page load. A remove button clears the frame and browser-local URL.
Persist only the widget URL (no feedback) in localStorage, tolerating failures.
Do not reuse Clever's demonstration widget ID. Keep the full branded frame
visible, with fixed generous height, responsive width, descriptive title,
strict-origin-when-cross-origin policy (allows the configured-site origin check)
and no top-level navigation permissions. The user can open
the service directly if embedding fails; do not infer loaded means ready.

Use existing generated/original comment and endnote data through a source
selector and Prepare button. Copy only prose using existing clipboard fallback;
provide a readonly preview for failed clipboard access. Refuse empty sources and
over-1500-word combined input, advising smaller selections. Do not postMessage
text, inspect cross-origin DOM or simulate submission. Clear the preview on new
review/reset or changing manuscript so stale feedback cannot be mistaken for
current feedback. No automatic result import or changes to downloads.

## Verification and release

Test URL validation including credential, origin, query and path attacks using
Node against exported pure validation function. Existing Studio parsing and
accessibility tests must pass. Verify browser layout, disabled setup state and
copy preparation without a third-party request, save screenshot, deploy to
localhost. A real embed cannot be verified until user supplies issued URL and
allows http://127.0.0.1:8000 in Clever account settings.

## Goldfish resolutions

Implement `portal/static/clever-widget.js` first, exporting `normalizeUrl`,
`feedbackText` and `mount` through CommonJS for Node tests and window.CleverWidget
for Studio. Then register it before studio.js in thinkingstorm_view.py, add the
panel in studio.html and style in workspace.css. Tests live in
tests/test_clever_widget.py alongside existing Studio tests.

Sources are `comments` (lastData.comments[].comment_text, blank-line separated),
`endnote` (endnoteText(lastData)), `original-comments` and `original-endnote`
(originalFeedback.comments_text/endnote_text). No combined selection. Invalidate
generated-source eligibility when manuscript input/mode/file changes or reset;
restore only after render of a successful review. Disable preparation during a
review, clear previews when sources change, and preserve prior eligibility on a
failed retry only if the manuscript has not changed.

User supplied an account-issued widget on this turn. Include its public URL as
the initial URL field value, never as a preloaded frame. A browser-local empty
string records removal so reloading does not restore the default URL.

Use the exact supplied embed settings: sandbox is allow-scripts allow-same-origin
allow-popups allow-popups-to-escape-sandbox; referrerpolicy is origin;
allow is clipboard-write. Height is 800px with normal internal scrolling; no
cropping of branding. External fallback is https://cleverhumanizer.ai/ opened
with noopener/noreferrer. Never claim a frame load event proves readiness.

Node fake-DOM behavior tests cover stored URL without iframe creation, explicit
load/removal, blocked storage, empty/1500/1501-word input, clipboard failure
preview, source text extraction, and clear/busy behavior. Browser verifies
manuscript changes invalidate generated source eligibility and setup rendering.
