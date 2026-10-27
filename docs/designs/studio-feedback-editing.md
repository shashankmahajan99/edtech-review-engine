# Edit feedback and save the reviewed DOCX

## Goal and scope

Reviewers edit comment bodies beside immutable quoted targets and edit the full
endnote in Studio. Save updates the same commented download. No reviewer/model
rerun, external submission, manuscript edits, anchor moves, adding or deleting
comments. Humanized text can be pasted directly into its original comment field.

## Server plan

Add portal/feedback_editor.py. On a successful Studio execute, register a
server-owned manifest under output/feedback-editor/<job>.json. Store raw and
commented filenames, reviewer identity, and SHA256 of a new 32-byte random edit
capability. Return the capability, current DOCX SHA256 revision, canonical native
comment IDs and actual native endnote text in the execute response. The manifest
is outside the generic single-filename download namespace. Do not expose tokens
in logs or QA reports. Existing jobs without manifests require a new review.

Register only when returned comment count matches native comment count and all
anchors are singular. Map comments in native order to immutable feedback_id;
read canonical bodies from Word instead of trusting display strings. If that
mapping cannot be verified, deliver the existing review with editing unavailable
and a reason, rather than invent an anchor association.

POST /api/thinkingstorm/feedback/{job_id} accepts JSON {edit_token, revision,
comments:[{id,body}], endnote_text}. IDs must exactly equal the native IDs, with
no duplicates; accept a permutation but retain native order. Bound total JSON
size to 128KB before parsing, strings to 10KB per comment and 32KB endnote; require
plain nonempty strings and XML-safe characters. Require a constant-time capability
hash match. Validate job format ts-[a-f0-9]{6,32}; filenames come only from the
server manifest, checked as basenames within output. Run work in a threadpool.

Serialize edits with a module RLock in the current single-process portal; compare
submitted revision to SHA256 of the current DOCX, return 409 on stale revisions.
Do not base revision on the mutable QA file or client body. Read native anchors
from the current Word document, rebuild only comment bodies with their existing
IDs/attributes/linked category and native closing note id1 using existing writer
helpers. All other ZIP members, especially document.xml and its anchor ranges,
stay byte-identical. Normalize comment whitespace into one paragraph; split the
endnote on blank lines, preserving the greeting/headings/signature paragraphs.

Write a temporary DOCX in output/feedback-editor, run validate_deliverable against
the raw manuscript model and original anchor quotes, edited bodies and endnote.
Its existing 6–95-word comment, punctuation, letter structure/signature, style and
native package checks remain mandatory. Rejection is 422 with readable errors;
do not alter last valid download. Success writes an immutable revision QA JSON
without credentials, then atomically replaces the public commented DOCX. Return
canonical comments/endnote, revision, no-cache versioned commented URL and QA URL.
Keep reports and mechanical tracked changes separate; they are not regenerated.
Set no-store headers on the commented download route.

## Client plan

studio.html adds Save feedback to DOCX, Discard edits and a live status in the
feedback card. studio.js renders labelled textareas in each comment beneath the
unchanged heading/quote and one endnote textarea. A new feedback-editor.js owns
dirty comparison, saving, error display and comment-download availability. It
reads the current rendered fields, posts explicit stable IDs and revision,
updates lastData through a callback only on success, and leaves drafts on failure.
No localStorage or background autosave. Copy buttons and Clever preparation use
the current editor draft. The canonical endnote may contain blank lines; UI
guidance explains preserving greeting, section headings and signature.

Disable commented download while dirty/saving, remove href, set aria-disabled,
restore the latest revision URL after successful save or discard. Do not disable
all downloads; other artifacts remain their original versions. Prevent new review
submission while dirty and require explicit discard before New review. Disable
editing/run/new-review during saving. Warn before leaving with unsaved edits.
The commented filename and /download/commented/{job_id} route stay compatible.
Register feedback-editor.js before studio.js and bump asset version.

## Tests and deployment

tests/test_feedback_editor.py builds real reviews from existing fixture DOCX,
edits two distinct comments and the note, reopens the download and asserts exact
saved text, stable IDs/quoted ranges, identical document.xml and untouched ZIP
members. Test revision conflict, missing/wrong token, ID tampering, invalid prose,
concurrent stale saves, failed validation preservation, payload/path limits and
successive saves after service restart (manifest reload). API tests verify payload
size, response and downloaded bytes. Client Node fake DOM tests cover dirty,
blocked download, successful/failed save, discard, draft copying and busy state;
Studio script and accessibility tests remain passing. Browser verifies editing,
saving, downloading actual revised DOCX and screenshot, then deploy locally with
the existing fast/local profile. No corpus or fixture regeneration.

## Goldfish resolutions and exact contract

Phase 1: implement portal/feedback_editor.py and tests/test_feedback_editor.py;
then hook registration and save endpoint in portal/server.py. Phase 2: create
portal/static/feedback-editor.js and tests/test_feedback_editor_js.py; integrate
portal/static/studio.js, studio.html, workspace.css, portal/thinkingstorm_view.py
and portal/ui.py. Phase 3: regression/browser/download checks and local deploy.

Manifest additionally stores immutable ordered anchors [{id,quote}], SHA256 of
word/document.xml and the raw input file hash. Registration compares each native
quote (whitespace-normalized) and native body to the corresponding displayed
target_text/comment_text before assigning feedback_id. Every save verifies the
current document.xml hash, native IDs and raw file hash against the manifest;
validation expectations use the persisted quotes, never new client targets.

Response additions: editing_available:boolean, editing_unavailable_reason:string
(only unavailable), edit_token:string, feedback_revision:string and per-comment
feedback_id:string. Registration canonicalizes endnote_text from native note1.
Success returns comments:[{id,body}], endnote_text, feedback_revision,
commented_docx_url, qa_report_url, saved_feedback:true and validation:{ok,...}.
Errors use FastAPI detail:string and status 400/403/404/409/413/422. All errors
retain drafts. JS global FeedbackEditor.mount({document,getData,onSaved,onDirty})
returns {reset,readDraft,isDirty,isSaving}; readDraft returns {comments,endnote_text}
where comments preserve metadata and substitute edited comment_text. Client reads
comment fields by data-feedback-index and endnoteEdit, not array position from a
server payload. Saving uses each preserved feedback_id and the current revision.

Live manual-path validation found an existing writer defect: it appended the
endnote marker after w:sectPr. Correct engine/thinkingstorm_engine.py to insert
that new marker before section properties on generation, with a native save
regression test. Editing still never changes document.xml; the initial manual
review must have valid Word ordering before its immutable identity is recorded.

## Humanized endnotes and actionable save errors

The reported closing note has plain headings followed by a single line break.
The old parser grouped heading/body into one paragraph and the validator counted
only paragraphs ending with a colon. This is an input-format bug, not proof that
the submitted feedback is invalid.

Phase 1: a pure engine/review/letter_format.py recognises existing colon headings
and known plain review headings (including Thesis, Evidence & Analysis, Specific
issues & links). Parsing reviewer input separates those heading lines and an
opening Dear greeting without changing words or adding colons. Shared recognition
is used by the native writer's bold styling and validator's section count. Keep
the 1–3-area, greeting, signature, comment and native-integrity gates intact.

Phase 2: portal/feedback_editor.py translates failed checks to structured issues
{field:comment|endnote|document, comment_id?:string, message:string}. An HTTPException
subclass retains detail:string for old clients and exposes issues for the route
to return beside detail. Messages name the displayed comment number, explain
the limit/structure failure and a concrete remedy. Document failures remain
separate from editable-text failures. Never echo edit tokens or raw XML.

Phase 3: feedback-editor.js retains the full draft, renders a persistent role=alert
issue list below the save bar, flags associated controls with aria-invalid, and
lets users jump to the affected field (switching to Endnote or Comments tab).
Clear only a corrected field's issues on input; preserve issues for other fields.
Use DOM textContent, not error HTML. Reset/discard/success clears all issues. Old
open clients still receive readable detail text and can retry after deployment
without reloading, regenerating feedback or losing their current edit capability.

Targeted tests: save the exact reported letter, retain all its words, recognise
three heading paragraphs and pass native validation; reject missing headings and
unsupported prose without changing the existing file; assert structured API
errors/one-based comment labels and client error-list/jump/clearing lifecycle.
Existing editor and native gate tests run as focused regressions. Deploy via the
existing fast/local profile without restarting or replacing the Cloudflare tunnel.

Goldfish resolutions: plain heading matching is whole-line only, case-insensitive,
trimmed and whitespace-collapsed, with `&` treated as `and`. The allowlist is:
Thesis, Thesis statement, Thesis and focus, Thesis and overall focus, Introduction,
Introduction and thesis, Abstract, Evidence, Analysis, Evidence and analysis,
Supporting evidence, Paragraph focus and connections, Organisation, Organization,
Organisation and flow, Organization and flow, Conclusion, Conclusion and
implications, Considering another perspective, Counterargument, Counterarguments,
Counterargument and response, Sentence clarity, Grammar and punctuation, Language
and style, Citation and document formatting, Citations and formatting, Specific
issues and links, Opening and personal focus, Programme fit, Program fit.
Mixed colon/plain headings work; a prose sentence containing these words does
not match. Markdown syntax is not inferred. Existing colon-ended single-line
headings remain supported.

Only reviewer save parsing changes; automatic letter composition and the legacy
manual-input wrapper remain unchanged. The save parser separates recognized
heading lines and the first Dear greeting line, retains all body wording and
never adds a greeting, colon, signature or sentence. The exact reported input is
a string fixture in tests/test_feedback_editor.py, not a regenerated DOCX fixture.

Map `comment <native id>:` errors using the manifest's ordered anchor IDs to the
visible one-based comment number. Aggregate banned-phrase errors are attributed
by rerunning the same banned_hits function per submitted body, suppressing
duplicate per-comment messages. Unattributable aggregate errors and unknown
native/package errors are document-level and do not flag an arbitrary editor.
Endnote errors identify that field and supply heading, greeting, signature or
word-count guidance. Preflight empty/oversize/XML errors also identify their
actual field. Backward-compatible detail concatenates readable messages for
existing open pages; new clients additionally show issue buttons and highlights.
