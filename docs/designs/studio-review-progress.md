# Actual Studio review progress

## User outcome

Replace the spinner-only wait with a progress bar driven by completed work.
Show the current step, checked/remaining feedback passages, elapsed time, and an
editing-time estimate when enough current-run observations exist. Never animate
the percentage based on a timer or promise a fixed finish time.

## Architecture and counts

Keep POST /api/thinkingstorm/execute backward compatible. Studio generates a
random 128-bit hex progress_id and submits it as an optional multipart field.
Poll GET /api/thinkingstorm/progress/{progress_id} once per second without
overlapping requests. Before the multipart upload has reached the handler, 404
means not registered yet; show indeterminate Uploading manuscript. A missing or
invalid tracking response never interrupts the review POST.

Add a thread-safe in-memory registry in portal/review_progress.py. The current
launcher runs one server process; this registry is not a multi-worker design.
The unguessable token is the read capability. No list endpoint or manuscript,
names, filenames, quotes, comments or exception details are exposed. Send
Cache-Control:no-store. Accept only 32 lowercase hexadecimal characters. Duplicate
IDs return 409 without replacing another job. Keep at most 256 entries, expire
terminal entries after 15 minutes and stale active entries after two hours;
evict oldest terminal entries first at capacity and reject if all 256 are active.
Use a lock for worker-thread updates and HTTP snapshots. Inject a monotonic
clock for tests. Updates after a terminal state are ignored.

There are four fixed completed-work units: load the manuscript, prepare feedback,
prepare/check the Word document, and prepare remaining downloads/save the job.
After composition, the number N of feedback passages is known: all comment
bodies plus narrative letter paragraphs except greeting, headings and signature,
using exactly the same eligibility rules as humanize_review. Total=N+4. Once
feedback is composed, completed=2. Each passage checked adds one, including a
deliberately preserved correction; retries do not advance it. All passages
checked gives N+2, Word validation gives N+3, and successful POST completion
gives N+4 (100%). Without the optional editor N=0, total=4. Before N is known,
remain indeterminate; do not guess a denominator. Counts describe work units,
not a percentage of seconds elapsed. Optional local review generation can take
longer before its passage count is known; its bar stays indeterminate then.

The humanizer supplies its actual completed/total counts before and after each
piece and announces a retry on the same piece without advancing. Compute ETA
only during editing, after at least three completed pieces and one elapsed
second: ceil(editing_elapsed/completed * remaining). Label it an estimate of
feedback-editing time only. Clear ETA during document/report finalization; do
not display zero seconds remaining while downloads are still being prepared.

## Implementation

1. Add engine/review/progress.py with a safe optional callback emitter; no
   network or inference. Observer exceptions cannot change a review result.
   Add progress=None to review_document and humanize_review. Emit manuscript
   loaded, reviewing, feedback_ready(N), passage-start/complete/retry, and
   document_ready only after the native Word validation succeeds. Compute N
   once from the exact list traversed by the editor. Direct CLI/Python use stays
   unchanged without a callback.
2. The registry callback consumes these events and exposes only status, stage,
   message, completed_units, total_units, percent, completed_passages,
   total_passages, remaining_passages, editing_eta_seconds and elapsed_seconds.
   Percent is floor(100*completed_units/total_units), capped at 99 until success;
   it is monotonic once the total is established. Failure never sets 100%.
3. Wrap the existing execute_thinkingstorm_pipeline route around an internal
   helper, forwarding all existing parameters explicitly. Register tracking
   before work, pass the callback to the pipeline worker, mark failure for any
   raised exception and re-raise the original HTTP behavior; mark completion only
   after the result/files/database write succeed. Manual feedback receives the
   fixed-unit milestones without claiming a model is running. Calls without a
   progress ID retain their old interface. Return 404 for missing progress IDs.
4. In portal/static/studio.html use native <progress max=100> with an accessible
   label and an absent value while indeterminate. Show current stage and a
   separate remaining/ETA line. Keep the existing three top-level navigation
   steps. Style the bar with existing theme colors, responsive layout and
   reduced-motion support.
5. In studio.js generate the token, begin polling, append progress_id and keep
   the existing POST/download/copy flow. Abort the current GET and clear its
   timer when POST succeeds/fails; ignore stale responses after a newer run.
   A failed poll preserves the last known bar and displays that updates are
   interrupted while the review continues. New/reset runs clear old counts.
   Terminal success is also rendered from the authoritative POST response.
6. Test registry counts, monotonic progress, retry stability, ETA clearing,
   capacity/TTL/privacy, duplicate tokens, terminal failure and unknown tokens.
   Test callback event order/remaining count and observer failure isolation,
   both portal success/failure routes, and frontend JavaScript parsing. Exercise
   a real localhost review and capture intermediate progress snapshots while
   the POST is pending. Verify it stays below 100% before success, counts agree
   with the final humanizer audit, and the Word release gate still passes.
   Then use the existing deployment helper and check the live UI.

## Goldfish review resolutions

The fresh-context architect/readiness review identified three Major gaps.
Resolve them before implementation:

- Buffer the UploadFile bytes in the async wrapper, then run the entire existing
  synchronous execution helper in one worker. Parsing, cleaning, manual generation,
  pipeline execution, redline/report creation and persistence all stay off the
  event loop. Remove the Studio helper's nested run_in_threadpool call. Test that
  progress GETs respond while manual work and report finalization are blocked.
- The third fixed milestone means Word file prepared. The automated pipeline
  emits it only after its native release gate; the legacy manual branch emits it
  after its existing generator returns. Do not label the manual milestone as a
  newly performed integrity check or change its validation behavior in this UI
  feature. Registry messages say Preparing downloads, not Validation passed.
- Each progress GET has a five-second timeout. Abort only that GET, show an
  interrupted-updates message, and schedule the next poll. The authoritative POST
  continues. Extract polling into review-progress.js so a Node test can exercise
  timeout/recovery, stale responses and cleanup without simulating the whole UI.
  Link that file before studio.js through the existing script renderer.
