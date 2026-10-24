# ThinkingStorm Deliverable Pipeline (v2)

Deterministic, offline review engine that turns a raw student `.docx` into the
same shape of deliverable the reviewer produces by hand:

`<original filename>_commented.docx`
- native Word margin comments anchored to the exact quoted sentence,
- ALL-CAPS knowledge-base link at the start of each labelled comment,
- a native Word endnote letter in red Times New Roman 12 pt, double spaced.

**No model calls, no network, no tokens.** The same input always produces the
same review, on any machine with Python and `python-docx`.

---

## 1. Why this replaces the old generator

| Old behaviour | v2 behaviour |
| --- | --- |
| Anchored `p[:80]` truncations, sometimes mid-word | Sentence segmentation with exact character spans; anchors always fall on word boundaries |
| 4-6 canned comments reused across every document | 40+ evidence rules, 3-4 phrasings per rule, chosen from the document fingerprint |
| One template endnote for every student | Three domain paragraphs composed from the findings, with per-document phrasing |
| No verification before download | A release gate re-opens the file and rejects it on any inconsistency |
| No way to run in bulk | CLI, batch mode, and a zero-token inbox watcher |

---

## 2. Pipeline stages

```
raw.docx
  │
  ├─ docmodel      paragraphs, runs, character offsets, regions
  │                (front matter / title / abstract / body / references)
  ├─ segmenter     abbreviation-safe sentences with exact offsets
  ├─ analysis      logical blocks → 40+ high-precision findings
  ├─ selection     budget, category caps, overlap checks, merged labels
  ├─ persona       human-register comment text (deterministic variant choice)
  ├─ endnote       three personalised domain paragraphs
  ├─ writer        OpenXML: run splitting, comments part, endnote part
  └─ validate      RELEASE GATE — any failure deletes the deliverable
```

Key design decision: rhetorical rules run over **logical blocks** (consecutive
paragraphs joined when a sentence is split across them), while every anchor is
still mapped back to one real paragraph, because a Word comment cannot span
paragraphs.

---

## 3. Release gate (what must pass before a file is shipped)

**Original file preserved.** The commented deliverable is the student's own
package: every part except `document.xml`, `comments.xml`, `endnotes.xml`, the
two relationships files, `styles.xml` and `[Content_Types].xml` is copied
byte-for-byte, and every paragraph's text is verified identical to the input.
The tracked-changes deliverable is edited in place: only `word/document.xml`
changes, and only the target span is wrapped in `<w:del>` / `<w:ins>` — fonts,
bold/italic runs, tables, images, headers and margins are untouched. Edits that
cannot be isolated safely (they cross a hyperlink or a non-text element) are
skipped instead of guessed at.

Structural
- opens with `python-docx`; all parts present (`comments.xml`, `endnotes.xml`,
  comments rels, content types);
- every original paragraph's text is byte-identical to the input;
- every comment id has exactly one range start and one range end in the same
  paragraph, followed by a matching `commentReference` run;
- no overlapping ranges, no duplicate ids.

Content
- 5-22 comments per review;
- 6-95 words each, terminal punctuation, no double spaces;
- the anchored text equals the quote the reviewer selected;
- every hyperlink resolves to an allow-listed
  `https://knowledge.thinkingstorm.com/` article;
- no comment repeats its own category label.

Style / AI-detector proxies
- no banned LLM vocabulary (`delve`, `tapestry`, `furthermore`, ...);
- sentence-length burstiness inside the human band;
- no repeated 5-grams across comments;
- varied sentence openers.

Endnote
- greeting, three domain headings, 120+ words, reviewer signature;
- every run Times New Roman, 12 pt, `FF0000`, 480-twip double spacing.

A rejected manuscript produces no deliverable. The reason is written to the
JSON sidecar and (in watcher mode) to `failed/<name>.error.txt`.

---

## 4. Command line

```bash
# one file
python -m engine.review.cli review draft.docx

# explicit output folder and style
python -m engine.review.cli review draft.docx --out deliverables --style apa

# inspect the diagnostics without writing anything
python -m engine.review.cli dry-run draft.docx

# a whole folder
python -m engine.review.cli batch ./inbox --out ./outbox

# self-check against the regression fixtures
python -m engine.review.cli selftest --fixtures tests/fixtures

# inspect the stylometric evidence for a finished deliverable
python -m engine.review.cli audit draft_commented.docx
```

`audit` prints comment count, per-comment lengths, sentence mean/variance,
5-gram repetition, opener variety, banned-phrase hits, and the endnote's own
metrics, then returns PASS or REVIEW. It is the quickest way to see *why* a
deliverable is unlikely to trip a detector — or which knob to adjust if it is.

Each successful run writes:

- `<name>_commented.docx` — the deliverable;
- `<name>_commented.review.json` — findings, selected comments, endnote, gate
  metrics. Useful for QA audits and for spotting a rule that fires too often.

Python API:

```python
from engine.review.pipeline import review_document

result = review_document("draft.docx", output_dir="out")
print(result.output_path, len(result.comments), result.validation.ok)
```

---

## 5. Hands-free operation (inbox watcher)

```bash
python -m engine.review.cli watch --inbox inbox --outbox outbox --interval 10
```

Drop a `.docx` into `inbox/`; within the interval the watcher writes the
deliverable and report into `outbox/`, then moves the source to `inbox/done/`.
Rejected files go to `inbox/failed/` with an `.error.txt` explaining why.
Processed files are recorded in `outbox/processed.json`, so restarting the
watcher never double-reviews a submission. Create `inbox/STOP` to stop it.

On Windows:

```powershell
.\start_ts_watcher.ps1        # background daemon + log tail
.\stop_ts_watcher.ps1
```

---

## 6. Genres

The engine classifies the draft before applying rules:

| Genre | Detected by | Rules that apply |
| --- | --- | --- |
| `argumentative` | modal claim + counterargument language | thesis, evidence, transitions, conclusion, counterargument |
| `research` (APA) | APA citations / references | abstract, thesis focus, evidence analysis, synthesis, APA mechanics |
| `rhetorical` | ethos / pathos / logos | rhetorical thesis, appeals analysis, clarity |
| `statement` | first-person density + admissions vocabulary | cliché opening, generic programme praise, missing specific fit, announced conclusion |
| `academic` | fallback | thesis, evidence, structure |

Personal statements skip thesis rules (a statement argues for a person, not a
proposition) and use the `Narrative and Opening / Specificity and Fit / Style and
Mechanics` endnote domains.

---

## 7. The reviewer persona (text register)

"Persona" here means **how the text sounds on the page** — diction, sentence
rhythm, directness, specificity — not audio, speech, or an impersonated person.
There is no TTS, no audio, and no voice cloning anywhere in this pipeline.

The persona exists for one reason: reviewer comments and an endnote letter that
read like generated text can be flagged by AI detectors, which would undermine
the deliverable. The controls are stylometric:

- no LLM vocabulary (`delve`, `tapestry`, `furthermore`, ...);
- sentence lengths deliberately uneven, inside the human band measured on the
  three real deliverables;
- no repeated 5-grams, no repeated opening phrases, no two same-sized notes in a
  row;
- specific, local detail in every note (the actual vague word, date, citation);
- different wording per document, reproducible for the same document.

Comments are mined from the three reference deliverables in
`style_corpus/exemplars.json` (Janeen, Andrea, Kiran). The rules:

- diagnosis first, then one concrete directive; occasionally a Socratic question;
- 20-45 words typical, but deliberately uneven — a short command next to a
  two-clause explanation;
- address the student directly ("you", "your paragraph"), never the document;
- name the actual thing: the vague word, the date, the citation, the studies;
- no hedging boilerplate ("it is important to note"), no LLM vocabulary.

The variant for a given finding is `sha1(document fingerprint | rule | position)`.
So two different drafts almost never share phrasing, and re-running the same
draft is reproducible.

---

## 8. Tests

```bash
python -m unittest discover -s tests -v
```

The suite covers document regions, segmentation edge cases, rule firing on real
drafts, absence of known false positives, composition determinism, banned
phrasing, endnote structure and typography, link allow-listing, the release
gate, refusal to re-review an already-commented file, and a static check that
no module imports a network or LLM client.

---

## 9. Portal integration

**Both website routes use this engine.** There is no second review path.

The Studio (`/thinkingstorm`) is a single screen: add a `.docx`/`.pdf`/`.txt` or
paste text, choose the style, run the review, then download:

- **Commented .docx** — the original file with margin comments and the endnote;
- **Tracked changes .docx** — the same original with mechanical edits as Word
  revisions;
- **Report .html** — rubric scores, priority actions and the summary;
- **QA report .json** — every finding, the gate metrics and the endnote.

Custom comments/endnotes live under an "Advanced" disclosure rather than a
separate mode. The page surfaces the server's error text verbatim.

`/api/thinkingstorm/execute` (the Reviewer Studio) returns the comments
(`category`, `target_text`, `comment_text`, `link_url`, `paragraph`), the three
endnote domains, the rubric, an executive summary, coverage counts, the QA report
URL and a `warning` when a fallback was used.

`/submit` (public intake) runs the same pipeline and produces all three
artifacts from one analysis:

- `_commented.docx` — the ThinkingStorm deliverable above (falls back to the
  legacy commenter only if the gate declines, e.g. a draft under 80 words);
- `_annotated.docx` — the original file with in-place tracked changes;
- `_report.html` — executive summary, priority actions, pillar breakdown and
  line edits.

Both docx downloads keep the student's formatting. The redline is not rebuilt
from text any more; the report carries the rubric and the summary.

### Full reviews

The pipeline defaults to `comprehensive=True`: roughly one note per 55 words
(cap 34), up to three notes on a substantial paragraph, and a coverage pass that
ensures every body paragraph containing a detected issue receives a comment.
`select_comments(..., comprehensive=False)` restores the lighter sampler for
callers that want it.

The rubric, the tracked changes and the report are computed by
`engine/review/report.py` from the same findings that drive the comments, so the
three deliverables cannot contradict one another. Scores are penalty-based
(25 per pillar, major rhetorical problems cost more than mechanical ones) and
verdicts name the specific issue that was detected.

### No model call by default

`engine/processor.py` only calls a model when **both** an API key is present
**and** `APEX_ENABLE_LLM=1` is set. Otherwise it computes the same deterministic
rubric. Nothing in the website requires a key, a network connection, or a token
budget.

### Accepted inputs

| Input | Handling |
| --- | --- |
| `.docx` | native comments and anchors on the real document; tracked changes are written from the analysed text |
| `.pdf` | text layer extracted with `pypdf`, then rebuilt into front matter + body paragraphs (`engine/review/ingest.py`) before review |
| `.txt` / pasted text | blank lines respected; otherwise sentences are regrouped into paragraphs |
| scanned PDF (no text layer) | **HTTP 400** with "No selectable text was found…", not a 422 |
| legacy `.doc` | **HTTP 400** asking for `.docx` |
| under 80 words | **HTTP 400** naming the word count |

If the release gate declines a readable manuscript, the Studio falls back to the
direct commenter and returns `warning` in the JSON instead of an error, so a
valid draft never dead-ends. The page shows the server's `detail` message rather
than a bare "Unprocessable Entity".

---

## 10. Adding a rule

1. Add the detector to `engine/review/analysis.py`, returning a `Finding` with a
   precise span, category, priority, and facts.
2. Add 3-4 phrasings to `TEMPLATES` in `engine/review/persona.py` using the facts.
3. Map the category to a knowledge-base article in `engine/review/links.py`.
4. Add a fixture assertion in `tests/test_review_pipeline.py`.
5. Run `selftest`; a new rule that fires on the header or on citations is almost
   always a false positive — anchor and precision matter more than coverage.

Priorities: 80+ for certain formatting errors and thesis problems, 60-79 for
structural rhetoric, 50-59 for stylistic observation. Selection spends its
budget from the top, caps each category, and allows one comment per paragraph
(two on short heading lines).
