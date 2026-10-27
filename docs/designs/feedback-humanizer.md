# Fast feedback humanizer

## Problem and decision

The deployed Strata reviewer took 1,641 seconds for a four-page Studio request.
The user rejects that latency and asks for a free humanizer on all generated
review comments and closing notes. Do not claim a detector threshold or human
authorship. Readability edits cannot establish either.

Evaluate `sgaofen/humanizer-local-model` with its dedicated Gemma-derived 12B
IQ2_XS-QAT completion model (3,893,632,896 bytes, published SHA-256
383e5ca8f1f48ab5f65013adbc1965fa70d1d1afa6c45d932c34b854e38edbb5).
The code is Apache-2.0. Keep upstream attribution, prompt, license and a source
revision in vendor/humanizer. Weights and the executable remain ignored output.
The model is a rewriting tool, not a reviewer. Its own evaluation reports factual
drift, particularly at this quantization. Validate real output before deployment.

Blader/humanizer and harshaneel/humanize are free editing instructions, not
standalone fast rewriting engines. Do not advertise installing a prompt as a
working runtime humanizer. The existing engine/anti_ai_humanizer.py makes false
detector guarantees, substitutes vocabulary and can inject unrelated diagnoses;
replace its unsafe comment transformation with the guarded implementation.

## Behavior and boundaries

The fast path uses the existing grounded rule reviewer, then a dedicated local
humanizer for prose. Strata becomes an explicit optional backend. Do not imply
the fast rule reviewer has the same editorial capability or page coverage as
the larger model. Preserve existing coverage warnings and show retained prose
when a rewrite is rejected. All automated comments and narrative closing-note
paragraphs are considered; category links, anchors, headings, greeting, signature,
original feedback extraction, user-supplied manual feedback and manuscript text
remain unchanged.

The humanizer receives one comment or letter paragraph at a time. It cannot move
a point between comments or rewrite the document. Match upstream raw completion
prompt and sampling exactly; do not use chat or reasoning mode. Run on a dedicated
loopback port 11437 with one slot and a short context. First try the already
installed CUDA llama-server; obtain official compatible binaries if necessary.
Free GPU memory by stopping only the verified workspace Strata processes once
the new model is ready for evaluation. Do not stop the independent speech service.

Protect quotations, URLs, numeric expressions and names/acronyms with reversible
placeholders. Reject missing, duplicate or invented placeholders, changed numeric
facts, changes to negation/conditional/uncertainty words, new first-person claims,
HTML, new headings, stock phrases, truncated output, out-of-range length or advice
polarity reversals. Preserve the corpus's no-contractions register. The checks
reduce obvious drift; they cannot prove semantic equivalence. At most one retry
per rejected piece, with an overall 180-second request budget. A still-rejected
piece keeps the original prose and creates a visible needs-review warning with
an actual count. Runtime unavailability rejects the request, rather than silently
claiming successful humanization. Do not add fake errors, irrelevant praise,
randomness to the rule reviewer, or detector-score estimates.

## Detailed Implementation Plan

1. Add a pure `engine/review/humanization.py` module accepting composed comments,
   an Endnote and a rewrite callable. Return edited comments, an Endnote with
   recalculated word count, and audit metadata. Preserve comment object identity,
   rule/category/span, domains and endnote evidence. Recompute coverage, depth,
   copied sentences and the native Word gate after editing. Check the full letter
   remains 138–382 words. Roll back letter edits if they violate those constraints
   and report the retained letter, never conceal it.
2. Add network transport in `engine/feedback_humanizer.py`, outside the offline
   review core. It owns local-only configuration, raw prompt building, exact
   upstream sampling, deadlines, a process lock, one retry, and completion-error
   handling. The core pipeline gets an optional `feedback_rewriter` callback;
   direct Python calls remain offline by default. No new external API dependency.
3. Inject the callback into both automated portal review routes and CLI
   review/batch/watch. Pass it through the watcher's public functions. The manual
   injection path and original-feedback endpoint remain exact. Prevent legacy
   fallback when the humanizer is configured and processing fails. Store audit
   metadata under generation.humanization, propagated into the existing quality
   response. Studio displays the actual rewrite/retained counts and warnings.
4. Add a saved runtime profile at ignored output/review-runtime.json with
   backend=rules and humanizer=local. Portal and CLI launchers read that explicit
   profile before the historical local-model/config.json auto-selection.
   Existing explicit environment/CLI backend overrides take precedence. A
   dedicated deployment helper verifies the humanizer health, backs up the old
   runtime profile, restarts only the recorded portal/watcher, waits for socket
   release, checks health and records the actual configuration/PIDs. Restart
   scripts reuse the downloaded model. Leave Strata files for explicit use.
5. Add tests for exact prompt fingerprint, localhost restriction, timeout and
   output truncation, placeholder collisions/missing/duplicates, numeric units,
   quotes, negations/qualifiers, polarity, unchanged anchors/headings/evidence,
   one greeting/signature, original feedback preservation, partial retention
   warnings, offline default and explicit profile precedence. Run the existing
   reviewer, Studio, source-feedback and Word integrity suites.
6. Benchmark the dedicated model on actual saved Taylor/Leland feedback before
   changing the default. Inspect prose manually. Then run a fresh full Studio
   request from an original DOCX using fast rules plus humanizer, verify copying
   and Word integrity, and measure the entire latency. Deploy only if it is
   materially faster than Strata (target under three minutes), protects facts,
   and makes no false all-rewritten claim. If it cannot meet these checks, keep
   the fast offline reviewer as default and document the model's rejection and
   pending humanizer rather than claim success. Retain the prior model profile
   for rollback. Do not upload private documents to public humanizer websites.

## Review resolutions and implementation contracts

The initial Goldfish reviewers identified missing lifecycle, guard, profile and
acceptance contracts. Resolve them as follows before implementation:

- Reuse coverage.assess, style_guard.banned_hits and validate_deliverable. Extend
  tools/deploy_local_reviewer.ps1 with Mode=local|fast rather than build another
  deployment controller. Only add a dedicated model-start helper.
- Pin code revision 7dd4be90cb3acb2e5d18aeea5837f888d2bb2d52 at
  https://github.com/sgaofen/humanizer-local-model and model revision
  2e57b6528a4070c33f3e09ca24e3325a84272f68 at
  https://huggingface.co/jialinyyzz/humanizer. Use its prompt_format.json;
  build_prompt('X') has SHA-256 prefix cc51d66b4c593fbe. Use /completion,
  temperature=1.0, top_p=.95, top_k=0, min_p=0, repeat_penalty=1.0, no stop
  strings; n_predict=min(2048,max(256,ceil(4*input_words))). Context=4096,
  parallel=1; require supported Gemma4 weights and a successful real self-test.
- Rewrite callable contract: str -> str; empty/truncated/transport failure raises
  RuntimeError and rejects the entire review. The pure guard owns one rejection
  retry, not the transport. An optional session() context manager bounds the
  entire humanization pass. The adapter acquires a nonblocking cross-process
  file lock (Windows msvcrt, Unix flock) and fails busy immediately; admission
  checks /slots for active work left by a disconnected request. It starts the
  180-second wall deadline before admission. Each HTTP call uses min(30,remaining)
  seconds. Exhaustion rejects the request. Close timed-out connections; subsequent
  sessions refuse admission until the single slot is idle. No unbounded queue.
- Merge overlapping protected ranges, preferring full quotations, then URLs,
  numbers/units, then capitalized names/acronyms. Use a per-text hash in exact
  placeholders that do not already occur in input. Restore only if every expected
  placeholder appears exactly once and no unknown placeholder exists. Protect
  every uppercase acronym; protect capitalized words except common sentence
  starters, and explicit student/reviewer name tokens. Numeric units include
  percent/%, money, common time/distance/mass units. Existing placeholder-like
  source text must round-trip as literal text. Match original/restored numeric
  and URL multisets. Expand ordinary contractions only outside protected spans.
- Compare occurrence counts for not/no/never/without/cannot/may/might/could/
  likely/possibly/if/unless outside protected spans. Reject changed counts or
  new first-person pronouns, HTML/fences/headings, stock phrases and newly
  introduced opposing advice groups (add/include/insert/provide versus
  remove/delete/omit/cut). These checks are deliberately conservative and do not
  establish semantic equivalence. Comments stay 6–95 words and between .65 and
  1.6 times original length; developmental comments originally >=25 words must
  retain that minimum. Letter prose uses the same ratio and at least six words.
- Endnote eligibility: preserve first paragraph (greeting), final two paragraphs
  (sign-off/name), and any paragraph ending in a colon. Consider other paragraphs
  with at least six words; record shorter narrative unchanged. After rewriting,
  recompute total word count. Roll back all letter edits only for a newly invalid
  138–382 range or newly repeated >=8-word comment sentences; pre-existing
  coverage warnings do not trigger rollback. Preserve domains/evidence verbatim.
- Audit schema: enabled, provider, model, elapsed_seconds, attempted, rewritten,
  unchanged, retained, retries, pieces[{kind,index,status,reason}], and
  detector_score=null. attempted counts eligible prose pieces, not retries;
  rewritten+unchanged+retained=attempted. Rolled-back pieces become retained,
  so totals describe delivered text. Any retained piece appends a quality warning
  and forces needs_review=true. UI shows actual rewritten/retained counts.
- Runtime profile schema: {backend:rules|local,humanizer:off|local,
  humanizer_config:absolute_path}. Default is output/review-runtime.json;
  TS_RUNTIME_PROFILE can select another file. Explicit CLI backend overrides
  TS_REVIEW_BACKEND, which overrides profile backend, which overrides the old
  local-model/config.json auto-selection. TS_HUMANIZER and TS_HUMANIZER_CONFIG
  override profile values. --backend local still uses profile humanization
  unless TS_HUMANIZER=off is explicit. Invalid configured profiles fail clearly.
  Direct pipeline calls do not read the deployment profile or call a model unless
  a callback is supplied. Portal launcher and CLI apply profile defaults.
- Mode=fast deployment verifies /health and expected /v1/models alias, backs up
  the previous profile, saves backend=rules/humanizer=local, then uses existing
  recorded PID command checks, port-release wait and startup health gate.
  Record new PIDs before health checks for recovery, but mark deployment success
  only afterwards. Mode=local saves backend=local/humanizer=off for explicit
  rollback; restarting Strata also requires freeing the dedicated humanizer GPU.
- Evaluation set: all 15 Taylor saved comments plus its 318-word letter from
  output/local-model/Taylor_Caruso_local_review.review.json, and the fresh Leland
  API feedback in output/local-model/portal-response.json. Inspect each changed
  piece for diagnosis/advice drift, invented facts, lost uncertainty and register.
  Require zero observed unguarded factual/advice errors, every protected token
  intact, and useful wording changes in >=60% of eligible pieces across the two
  reviews. Report rejected/retained pieces explicitly. An unchanged output does
  not count toward useful coverage. Require a fresh Studio request under 180
  seconds and native Word preservation before activation. If acceptance fails,
  deploy backend=rules/humanizer=off to remove the rejected Strata default and
  report that the humanizer remains unapproved. This fallback does not claim
  model-level diagnosis quality or silently humanize anything.

Final Goldfish findings resolved: after any letter-only rollback, reassess the
complete comments/letter combination. If any newly copied margin sentence still
exists, revert all changed prose to its original text and record those pieces as
retained with a repetition reason. Test a rewritten comment that collides with
an unchanged original letter. Never claim the rollback itself fixes a collision.

Humanizer configuration has exactly base_url (loopback HTTP), model
(`thinkingstorm-humanizer`), prompt_path (absolute pinned prompt JSON), optional
budget_seconds (default 180, range 1–180) and call_timeout_seconds (default 30,
range 1–30). Reject unknown keys, invalid types or malformed files. The adapter
owns output/humanizer/review.lock under this workspace; callers cannot supply
arbitrary lock paths. Verify the expected alias from /v1/models and that /slots
is idle before completion requests. The model startup and deployment helper use
this same file at output/humanizer/config.json.

## Evaluation change: dedicated model rejected

The dedicated 12B IQ2 model passed transport and Word checks but failed editorial
acceptance on Taylor: only 6 of 20 pieces were rewritten safely (14 retained),
and several accepted outputs used a poorer, colloquial register. It is not the
deployment candidate. Preserve the traces as evidence; do not lower the gate.

Evaluate Blader's MIT Humanizer guidance at revision
8c307f367c91bd974002f10f2be2965d642c13df with an academic-specific instruction
prompt and the official Ollama Qwen3.5-4B Q4 language layer. SHA-256 is
a9d0a3e1d8c91732a3812becd31f8d4a8ff57414903f226306069f0437e2ac50.
This 2,648,593,216-byte model is a copyeditor only, not a replacement diagnosis
model. It fits fully on the GPU; reasoning is disabled. Extend the same adapter
with provider=instruct, alias=thinkingstorm-editor, prompt_path pointing to
vendor/humanizer/editor_prompt.txt, /v1/chat/completions, temperature=.4, top_p=.9,
max_tokens matching the existing piece limit, enable_thinking=false. The raw
completion provider remains a diagnostic option. No other architecture or
acceptance thresholds change. Match configured provider to its expected alias;
the default startup helper selects the instruction editor after evaluation.

## Final rollout decision

The 4B trial was fast but had observed advice/grammar defects. Reuse the existing
official Qwen3.5-9B language layer (SHA-256
02d45dc1cf451ba2475ac33b301c2dd8f985abe4c182ce04a1f2f5bf0260278d) with the same
copyediting prompt, short context and disabled reasoning. Official b11335 fits
all 33 layers on this GPU; this differs from the earlier slow review-generation
trial using the Ollama fork and a larger context.

Protect whole dates and explicit replacement instructions. Whole quoted spans
remain exact; expose their terminal punctuation as a surrogate while editing,
then remove that surrogate before restoration to avoid doubled punctuation.
Normalize a newly introduced 'must' back to the source's 'should' where the
source only made recommendations. An imperative can express the same instruction
without retaining every 'should'; do not treat word counts as semantic proof.
Allow a capitalized common word already present lowercase in the source rather
than treating sentence capitalization as a new named entity.

The 9B saved-review trials changed 22/39 passages, left four unchanged and retained
13 after failed preservation checks. They took 90 and 67 seconds. This fails the
proposed 60% utility threshold for fully automatic humanization, so withdraw that
approval claim. Ship only guarded editing with actual counts and visible
needs-review retention warnings, as requested; never label all passages humanized.
The fast profile removes Strata from the default. Original diagnosis coverage is
still assessed separately. Fresh website checks and native Word integrity remain
mandatory before deployment. Config also permits provider=completion|instruct and
an optional model_name for truthful display; the active alias remains
thinkingstorm-editor and model_name=qwen3.5:9b.

The first fresh-site comparison found another concrete defect: capitalized
sentence-opening words (Apply, Dates, Could, Attach) had been masked as names.
Disable rewriting while fixing that classifier. Keep ordinary sentence starters
visible, but protect known student/reviewer names and reference surnames even at
sentence starts. The next manual comparison caught a rewrite describing a
suggested paragraph break as already marked. Require advice to remain advice and
reject newly invented completed-edit claims. Regression tests cover both cases;
the corrected fresh runs and 162 affected tests passed before guarded editing
was re-enabled. These checks do not establish universal semantic equivalence.

## Cutoff recovery correction

A live request exposed an inconsistent failure boundary: an unsafe candidate was
retained safely, but a candidate that reached its output limit aborted the whole
review. Classify cutoff responses as TruncatedRewrite, a rejected candidate. Use
the existing single retry, then retain the complete original passage with a
visible warning if both attempts fail. Never return the partial response. Keep
runtime outages and invalid protocol responses fatal. Record truncated_attempts
in the audit. Regression cases cover both transports, repeated cutoffs with a
valid Word result, and a successful retry after one cutoff.
