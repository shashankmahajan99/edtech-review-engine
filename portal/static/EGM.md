# Portal Browser Assets (Studio & Workspace UI)

## Overview

Browser-side assets for the Apex portal. FastAPI mounts this directory as the
static root in `portal/server.py`:

```python
app.mount("/assets", StaticFiles(directory=PROJECT_ROOT / "portal" / "static"), name="workspace-assets")
```

The package backs exactly one page today: the ThinkingStorm Studio at
`/thinkingstorm`. `portal/thinkingstorm_view.py` reads `studio.html`, wraps it
with the shared shell from `portal/ui.py` (`workspace_page`), and emits links of
the form `/assets/<file>?v=<ASSET_VERSION>` for `workspace.css`, `workspace.js`
and any page script. `ASSET_VERSION` is `"20261026-humanized-save2"` in
`portal/ui.py`, so the static URL prefix and cache-busting version come from
Python, not from these files. The Studio script order is
`review-progress.js`, `clever-widget.js`, `feedback-editor.js`, `studio.js`
(all `defer`, so they execute in document order before `DOMContentLoaded`).

| File | Role |
| --- | --- |
| `studio.html` | Studio body markup only — a fragment, no `<html>`/`<head>`; injected into `workspace_page`. |
| `studio.js` | Studio controller: input modes, upload validation, review execution, progress polling, rendering, copy-to-clipboard, Clever and feedback-editor wiring. |
| `feedback-editor.js` | `FeedbackEditor.mount(...)`: tracks the comment/endnote draft against the saved DOCX, saves through the capability token, blocks the download while dirty. |
| `review-progress.js` | `ReviewProgress.start({id, onUpdate, onUnavailable})`: 1 s polling of the progress endpoint with a 5 s per-request timeout. |
| `clever-widget.js` | `CleverWidget.{normalizeUrl, feedbackText, mount, mountDetector}`: URL-allow-listed Clever Humanizer/detector embeds and the manual copy handoff. |
| `workspace.css` | Design system and layout for the whole workspace shell; tokens live in `:root`. |
| `workspace.js` | Shared sidebar navigation behaviour (open/close, focus trap, inert regions). |

Every script is a hand-written plain-script IIFE (no `import`/`export`) except
that `feedback-editor.js` and `clever-widget.js` also expose their API through
`module.exports` when `require`d by the Node tests. There is no bundler, no
`node_modules`, and no build step; files are served verbatim.

## Problem & Scope

- These are the only browser assets the portal serves: the ThinkingStorm Studio page
  and the shared workspace shell (CSS plus navigation script).
- `portal/thinkingstorm_view.py` reads `studio.html` and wraps it in the Python shell
  from `portal/ui.py`; the static URL prefix and cache-busting version come from
  Python, not from these files.
- Scope is one page (`/thinkingstorm`) plus the shared shell used by other
  server-rendered pages. There is no bundler, `node_modules` or build step; the files
  are served verbatim.
- The assets own no server state. Their only persistence is the Clever widget URL,
  which `studio.js` passes to `clever-widget.js` as `localStorage` (when available).

## Goals & Non-Goals

- Goal: keep the Studio usable without a CDN — no Tailwind, Alpine or web fonts in the
  shell.
- Goal: keep markup and script in sync. Every id the scripts drive must exist in
  `studio.html`; tests assert tab wiring, label coverage and escaped user identity.
- Goal: keep every linked script parseable under `node --check`, because a syntax
  error silently kills upload and submit.
- Goal: make the commented DOCX a save consequence, not a side effect — the draft
  lives in the textareas, and the download is only linked while the draft matches the
  saved revision.
- Non-goal: a client-side router or a second page. The Studio is the only page this
  package backs.
- Non-goal: sending feedback to Clever automatically. The Clever panels prepare and
  copy text; submitting and pasting the rewrite back is manual.
- Non-goal: rendering arbitrary server strings as HTML. Values pass through `esc()` or
  `textContent`.

## Alternatives Considered

- A bundled SPA: rejected because there is no build step and the server renders every
  other page; a bundler would add a toolchain the deployment does not have.
- Fetching Tailwind from a CDN like the other pages: rejected for the Studio so the
  page works offline and `test_studio_ui.py` can assert the CDN string is absent.
- Putting the Studio markup in `server.py`: rejected; `thinkingstorm_view.py` reads
  `static/studio.html` on every request and `ui.py` owns the shell.
- Trusting server-provided URLs directly: rejected; `downloadPath` and `knowledgeURL`
  allow-list same-origin `/download/` and `knowledge.thinkingstorm.com` only.
- Re-posting the whole manuscript to save edited feedback: rejected in favour of the
  capability-token save (`/api/thinkingstorm/feedback/{job_id}`), which edits only the
  comment and endnote parts and keeps the anchors.
- Server-sent events for progress: rejected; one polling endpoint plus
  `review-progress.js` is enough for a single-review page and needs no server state.
- Calling Clever's API from the browser: rejected; the widget iframe and a manual
  copy/paste handoff keep the feedback inside a flow the reviewer controls.

## Risks & Mitigations

- A syntax error in any linked IIFE silently disables upload and submit. Mitigation is
  `tests/test_studio_js.py` running `node --check` on every referenced script.
- A markup id rename breaks the scripts with no defensive lookup. Mitigation is
  `tests/test_studio_ui.py` and the "every id must exist" invariant.
- The client-side 20 MB gate is advisory: `/submit` and `/api/thinkingstorm/execute`
  have no server-side size check (only `/api/thinkingstorm/original-feedback` caps at
  20 MB, and the feedback save caps its JSON body at 128 KB). Mitigation is a
  server-side cap; this contract only documents the asymmetry.
- An edited draft that is never saved could be mistaken for the deliverable.
  Mitigation: `feedback-editor.js` removes the commented-download `href` while dirty
  or saving, and `beforeunload` warns.
- The clipboard fallback uses a transient off-screen `<textarea>` plus the deprecated
  `document.execCommand('copy')`; mitigation is the primary
  `navigator.clipboard.writeText` path and the fallback only when it is unavailable.
- A learned Clever widget URL is stored in `localStorage`. Mitigation: it is only the
  embed URL (never feedback), loading it is an explicit button, `normalizeUrl`
  rejects anything but the exact `widgets.cleverhumanizer.ai/embed/<32 hex>`
  shape, and storage failures degrade to "URL was not saved".
- Escaping relies on `esc()` and fixed templates; a new interpolation that bypasses
  them would allow injection. Mitigation is the "all server strings pass through
  `esc()`" invariant.

## Interface

### `studio.html` — required DOM ids

The scripts and stylesheet address elements by id, so these ids are the
contract between markup and code:

- Progress rail: `stepManuscript`, `stepReview`, `stepDownload`; `workspaceStatus`.
- Form: `reviewForm`; mode tabs `uploadMode` / `pasteMode` with panels
  `uploadPanel` / `pastePanel` (`data-mode`, `role="tab"`).
- Upload: `dropZone`, `fileInput` (`accept=".docx,.pdf,.txt,.md"`),
  `chooseFileBtn`, `fileName`, `fileHint`, `fileControls`, `removeFileBtn`.
- Original feedback: `originalFeedbackPanel`, `originalFeedbackStatus`,
  `copyOriginalCommentsBtn`, `copyOriginalEndnoteBtn`.
- Paste: `manuscriptText`, `textHint`, `wordCount`.
- Details: `studentName`, `academicStyle` (`auto` | `mla` | `apa`),
  `reviewerName` (default `Raunak Banga`), `reviewerInitials` (default `RB`),
  `reviewerSummary`, `customComments`, `customEndnote`.
- Actions and status: `runBtn`, `runBtnLabel`, `inputError`, `statusLine`.
- Live progress: `loadingState`, `reviewProgress` (`<progress max="100">`),
  `progressTitle`, `progressPercent`, `progressDetails`, `progressEstimate`.
- Results: `feedbackPanel`, `emptyState`, `results`, `errorBanner`,
  `warningBanner`, `resultStatus`, `newReviewBtn`, `studentLabel`, `jobId`,
  `statsGrid`, `summary`, `reviewCoverage`, `downloads`, `qaDownload`.
- Feedback saving: `feedbackSaveStatus`, `saveFeedbackBtn`,
  `discardFeedbackBtn`, `feedbackSaveErrors`, plus `commentedDownload` (the
  primary download link, created inside `#downloads`).
- Feedback tabs (role `tab`/`tabpanel`, `data-tab` = `comments` | `endnote` |
  `rubric`): `commentsTab` / `tab-comments`, `endnoteTab` / `tab-endnote`,
  `rubricTab` / `tab-rubric`, `commentCount`. The comment and endnote panels are
  generated: `#commentEdit<i>` (`data-feedback-index="<i>"`, `maxlength="10000"`)
  and `#endnoteEdit` (`maxlength="32000"`).
- Clipboard: `copyCommentsBtn`, `copyEndnoteBtn`, `copyState`.
- Clever: `cleverPanel`, `cleverSource`, `cleverPrepare`, `cleverStatus`,
  `cleverPreview`, `cleverUrl`, `cleverOrigin`, `cleverFrame`, `cleverLoad`,
  `cleverRemove`; detector panel `cleverDetectorPanel`, `cleverDetectorLoad`,
  `cleverDetectorClose`, `cleverDetectorStatus`, `cleverDetectorFrame`
  (`data-widget-url`).

### `studio.js` — public surface

Internal IIFE; no globals are exported. The observable interface is the four
HTTP calls and the DOM ids it drives.

- `POST /api/thinkingstorm/execute` — `multipart/form-data` with
  `student_name`, `reviewer_name`, `reviewer_initials`, `academic_style`,
  `text`, `custom_comments_text`, `custom_endnote_text`, `progress_id`
  (32 hex chars from `crypto.getRandomValues`) and `file` (upload mode only).
  Response JSON is consumed by `render(data)`, which requires
  `Array.isArray(data.comments)` and `data.job_id` and otherwise throws
  "The server returned an incomplete review."
- `POST /api/thinkingstorm/original-feedback` — sent once per selected `.docx`
  (`{comment_count, comments_text, endnote_text, endnote_source}`); aborted via
  `AbortController` and guarded by a monotonic `originalSequence` so a stale
  response can never overwrite a newer one.
- `GET /api/thinkingstorm/progress/{id}` — only through `ReviewProgress.start`,
  which polls every 1000 ms, aborts a poll after 5000 ms, treats 404 as "upload
  has not reached the handler yet", and stops on `status` `complete`/`failed`.
- `POST /api/thinkingstorm/feedback/{job_id}` — only through
  `FeedbackEditor.mount`, as JSON
  `{edit_token, revision, comments:[{id, body}], endnote_text}`.
- Named functions: `setProgress`, `resetReviewProgress`, `showReviewProgress`,
  `trackReviewProgress`, `clearErrors`, `inputError`, `activateMode`,
  `updateFile`, `originalCopyAvailability`, `showOriginalFeedback`,
  `loadOriginalFeedback`, `validFile`, `selectFeedbackTab`, `downloadPath`,
  `knowledgeURL`, `endnoteText`, `render`, `setBusy`, `showReady`, `copyText`,
  `copy`, `copyOriginal`, `invalidateCleverFeedback`.
- Window globals consumed from other files: `ReviewProgress`, `CleverWidget`,
  `FeedbackEditor`. Only progress has a fallback — `trackReviewProgress` skips
  the token and writes "Live progress is unavailable" when
  `crypto.getRandomValues` or `ReviewProgress` is missing; the Clever widget and
  the feedback editor are called unguarded, so their scripts must load (in the
  order `thinkingstorm_view` lists them).
- `downloadPath(value)` resolves `value` against `window.location.origin` and
  returns a path only when it is same-origin and begins with `/download/`;
  anything else becomes `''` and the link is filtered out of `#downloads`.
- `knowledgeURL(value)` returns a URL only for `https:` +
  `knowledge.thinkingstorm.com`.
- Clipboard controls: `copy('comments')` joins every `comment_text` with
  `\n\n`; `copy('endnote')` uses `endnote_text`, falling back to
  `endnote_domains` joined as `heading + ':\n' + body`. Both copy the *current
  draft* (`feedbackEditor.readDraft()`) when an editor is mounted.
  `copyOriginal('comments' | 'endnote')` copies text captured from the uploaded
  DOCX. Feedback is shown in `#copyState` / `#originalFeedbackStatus`
  (`role="status"`) and the shared `#copyState` message clears after 4000 ms.

### `feedback-editor.js` — public surface

`FeedbackEditor.mount({document, getData, onSaved, onDirty, fetch})` returns
`{reset, readDraft, isDirty, isSaving}`.

- `readDraft()` overlays the textarea values on `getData()`'s comments and
  endnote; it never rewrites `target_text`, quotes or categories.
- `isDirty()` is `false` when `data.editing_available` is falsy, so a review
  without a capability token has no editable state.
- `refresh(message)` disables `#saveFeedbackBtn`/`#discardFeedbackBtn`
  appropriately, disables every comment/endnote field while saving or when
  editing is unavailable, and only leaves `#commentedDownload` linked when the
  draft is clean and the URL matches
  `^/download/commented/ts-[a-f0-9]{6,32}(?:\?revision=[a-f0-9]{64})?$`.
- A failed save renders `#feedbackSaveErrors` (a `<ul>` of buttons that jump to
  the offending field, plus `aria-invalid`/`aria-errormessage`), and keeps the
  draft. `onSaved(result)` hands back `comments`, `endnote_text`,
  `feedback_revision`, `commented_docx_url` and `qa_report_url`.

### `review-progress.js` — public surface

`ReviewProgress.start({id, onUpdate, onUnavailable, fetch, intervalMs = 1000, timeoutMs = 5000})`
returns `{stop}`. `stop()` clears timers and aborts the in-flight request; late
responses after `stop()` are ignored (the tests assert this). Polling observes
the review POST and never cancels or retries the document work.

### `clever-widget.js` — public surface

- `normalizeUrl(value)` accepts only
  `https://widgets.cleverhumanizer.ai/embed/<32 hex>` with an optional
  `?theme=light|dark|auto` and returns the canonical `?theme=` URL; every other
  shape (extra parameters, fragments, `http:`, look-alike hosts, userinfo,
  path traversal, raw `<iframe>` markup, `javascript:`) throws.
- `feedbackText(source, review, original, endnote)` returns the text for
  `comments`, `endnote`, `original-comments`, `original-endnote`; unknown
  sources and a missing review return `''`.
- `mount({document, storage, copyText, readFeedback})` restores the saved URL
  from the `thinkingstorm.cleverWidgetUrl` storage key without contacting
  Clever, creates the iframe only on `#cleverLoad`
  (`sandbox="allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox"`,
  `allow="clipboard-write"`, `referrerPolicy="origin"`), and prepares at most
  1,500 words per handoff. A copy that resolves after `clear()` cannot restore
  stale text. Returns `{clear, setBusy}`.
- `mountDetector({document})` loads the detector iframe from
  `#cleverDetectorFrame[data-widget-url]` only on click and can close it again.

### `workspace.js` — public surface

IIFE with no exports. Binds `navToggle`, `workspaceSidebar`, `navBackdrop`,
`navClose`; toggles `body.navigation-open`, sets `inert`/`aria-hidden` on the
sidebar and `.workspace-body`, promotes the sidebar to `role="dialog"` +
`aria-modal="true"` below 1024px, closes on Escape/backdrop/close button, traps
Tab across the sidebar's links **and buttons**, and restores focus to the
previously focused element. It re-runs `syncVisibility()` on
`matchMedia('(max-width: 1024px)')` changes.

### `workspace.css` — public surface

`:root` tokens: `--canvas`, `--surface`, `--ink`, `--muted`, `--line`,
`--accent`, `--accent-dark`, `--accent-soft`, `--nav`, `--nav-text`, `--radius`;
`color-scheme: light`. Layout classes consumed by the markup include
`.apex-app`, `.workspace-sidebar`, `.workspace-body`, `.workspace-topbar`,
`.workspace-main`, `.workspace-footer`, `.workspace-link.is-current`,
`.skip-link`, `.sr-only`, `.nav-backdrop`, plus the Studio-specific
`.page-intro`, `.review-steps`, `.studio-grid`, `.manuscript-panel`,
`.upload-zone`, `.feedback-card`, `.feedback-tabs`, `.feedback-content`,
`.feedback-toolbar`, `.comment-item`, `.rubric-table`, `.rubric-score`,
`.review-stat`, `.download-grid`, `.download-link`, `.message-banner`,
`.review-progress-heading`, `.progress-estimate`, `.feedback-save-bar`,
`.feedback-save-errors`, `.comment-editor-label`, `.feedback-issue-link`,
`.clever-panel`, `.clever-frame`.
Not every id in `studio.html` has a rule: `.feedback-panel` (the results column)
is laid out purely by `.studio-grid`, and the drop zone is styled as
`.upload-zone`.

## Invariants

- Every linked script must parse: `tests/test_studio_js.py` runs `node --check`
  on every `/assets/*.js` referenced by the rendered Studio page, and the
  Node-driven suites `require` `feedback-editor.js`, `clever-widget.js` and
  `review-progress.js` directly. A syntax error here silently kills upload and
  submit.
- Every id referenced by the scripts must exist in `studio.html`, because the
  fragment is concatenated into one document with no defensive lookups. Ids
  created dynamically (`#commentEdit<i>`, `#endnoteEdit`, `#commentedDownload`)
  are produced by `render(data)`.
- Each `[role="tablist"]` keeps exactly one `aria-selected="true"` tab, every
  tab is `type="button"`, and every `aria-controls` points at a real id with no
  duplicate ids (`tests/test_studio_ui.py`).
- Every `input`/`select`/`textarea` has a `<label for=…>` or an `aria-label`;
  `#inputError` is `role="alert"`; `#statusLine` is `aria-live="polite"`.
- The Studio shell carries no CDN dependency — `test_studio_ui.py` asserts
  `cdn.tailwindcss.com` is absent from the rendered page. `studio.html` must not
  introduce Tailwind, Alpine or web fonts. (The Clever iframes are external but
  only load on an explicit click and are not part of the shell.)
- All server-provided strings pass through `esc()` before insertion into
  `innerHTML`. Injected markup is limited to fixed templates plus escaped values;
  `textContent` is used for summaries, banners, status lines and save issues.
- Minimum-length rule: pasted text shorter than 80 words is rejected client-side
  unless the user supplied custom comments or a custom endnote (the server
  enforces 80 words independently for automatic reviews).
- File gate before upload (client only): `validFile` requires an extension in
  `.docx|.pdf|.txt|.md`, non-zero size, and at most 20 MB. Server-side the cap
  exists only on `/api/thinkingstorm/original-feedback` (`server.py:1622`);
  `/submit` and `/api/thinkingstorm/execute` read the whole upload with no size
  check, so a non-browser client bypasses the gate.
- Download and category links are allow-listed (`/download/…` same-origin,
  `https://knowledge.thinkingstorm.com`); arbitrary URLs from a review payload
  are never rendered as links.
- Draft state and the DOCX stay consistent: the commented download is
  unlinked while `FeedbackEditor.isDirty()` or `isSaving()`, `runBtn` and
  `newReviewBtn` are disabled while saving or dirty, and submitting with unsaved
  edits shows "Save or discard your feedback edits before running another
  review" and focuses `#saveFeedbackBtn`.
- Only the Clever widget URL is persisted (`thinkingstorm.cleverWidgetUrl` in
  `localStorage`, when storage is available). No feedback, manuscript text,
  session data or review payload is written to `localStorage`,
  `sessionStorage` or cookies by these files.
- `busy` gates submission, drag/drop, file removal, "New review" and the Clever
  "Prepare" button so only one review request is ever in flight; `setBusy`
  disables form controls, calls `cleverWidget.setBusy`, and sets
  `#feedbackPanel[aria-busy]`.
- Controls are disabled until data exists: the two "copy original" buttons stay
  disabled unless the extracted `comments_text` / `endnote_text` is non-empty,
  and the save/discard buttons stay disabled unless editing is available and the
  draft is dirty.
- Progress is advisory: if `crypto.getRandomValues` or `ReviewProgress` is
  missing, or polling fails, the UI says so and the review continues; the page
  only trusts `complete`/`failed` and the final POST response.

## Side Effects

- Network: same-origin `fetch` only — one to `/api/thinkingstorm/execute` per
  submission, one to `/api/thinkingstorm/original-feedback` each time a `.docx`
  is selected, 1 s polling of `/api/thinkingstorm/progress/<id>` while a review
  runs, and one `POST /api/thinkingstorm/feedback/<job>` per save. The only
  third-party traffic is the Clever iframe (load/download/check), created only by
  the user's buttons, and the allow-listed knowledge link opened with
  `rel="noopener noreferrer"`.
- Clipboard: writes to the system clipboard through
  `navigator.clipboard.writeText`, falling back to a transient off-screen
  `<textarea>` + `document.execCommand('copy')`; the fallback restores the
  previously focused element.
- DOM: mutates `hidden`, `disabled`, `aria-*`, `innerHTML` of result regions,
  `body.navigation-open` and `inert` flags; scrolls `#loadingState` and
  `#feedbackPanel` into view and moves focus to `#results`, `#errorBanner`,
  `#feedbackSaveErrors` or the offending input.
- Browser storage: `localStorage['thinkingstorm.cleverWidgetUrl']` only, written
  by `#cleverLoad`/`#cleverRemove` through the injected `storage` object and
  swallowed when unavailable.
- Timers: one 4000 ms `setTimeout` clears the copy confirmation, replaced on each
  copy; `review-progress.js` owns a 1000 ms poll timer plus a 5000 ms abort
  timer, both cleared by `stop()`; `matchMedia('(max-width: 1024px)')` change
  listener re-syncs navigation visibility.
- Navigation guard: `beforeunload` prompts while the feedback draft is dirty or
  saving.
- Disk/state: none. These files never read or write files or cookies; the server
  owns all persistence in `output/` (including `output/feedback-editor/`) and
  `orchestrator/desk_jobs.db`.

## Verification

- Run: `python -m unittest discover -s tests`
- Studio-specific coverage: `tests/test_studio_js.py` (`node --check` on every
  linked script, skipped when `node` is not installed),
  `tests/test_studio_ui.py` (accessible names, tab/panel wiring, escaped user
  identity, no Tailwind CDN), `tests/test_feedback_editor_js.py` (dirty/save/
  discard/download lifecycle and save-issue focus), `tests/test_clever_widget.py`
  (URL allow-list, manual handoff, stale-copy protection),
  `tests/test_review_progress.py` (poll timeout recovery and stale-response
  cleanup). The Node-driven suites skip when `node` is unavailable. End-to-end
  review behaviour is browser-tested.
- Manual: run `python run_portal.py` and open `/thinkingstorm`; the served asset
  URLs must carry the `?v=20261026-humanized-save2` version from `portal/ui.py`,
  the progress bar must advance during a review, and "Save feedback to DOCX"
  must re-link the commented download with a `?revision=` query.
