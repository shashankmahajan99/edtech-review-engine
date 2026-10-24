# Reviewer voice and anti-detection practice

Built from 25 reviewed documents by Mehak and Mohini (307 native comments,
3 endnote letters). Regenerate the numbers with:

```
python tools/mine_voice_corpus.py "C:\Users\shashank\Downloads\Doc examples"
```

Outputs: `style_corpus/voice_corpus.json` (every comment with its anchored
text), `style_corpus/voice_profile.json`, and `docs/VOICE_PROFILE.md`.

## What the corpus actually does

| Measure | Corpus | Template output before tuning |
| --- | --- | --- |
| Words per comment | mean 26.9, σ 13.6, range 5–100 | mean 23.0, σ 6.9 |
| Sentence length | mean 14.3, σ 7.9 | mean 12.0, σ 3.8 |
| One-sentence comments | 46% | 11% |
| Questions | 11% | 3% |
| Hedges (“a bit”, “maybe”, “seems”) | 39% | 17% |
| Direct instructions | 47% | high |
| Specific reference to the student's words | 32% | low |
| Contractions | **0%** | 0% |
| First person (I / I'd / my) | 2.6% | rare |
| Labels | ALL CAPS + colon (`THESIS STATEMENT:`) | yes |

The gap that matters for detectors is not vocabulary, it is **rhythm**: the
reviewers alternate 6-word notes with 60-word explanations. Template prose is
uniform, which is what a detector measures.

## What the generator now does

- **Shape mix.** 40% of notes are the observation alone, 60% observation plus
  advice — matching the corpus's 46% one-sentence rate.
- **Hedges.** Every third comment with advice opens it with “Maybe” or
  “Perhaps”, on top of templates that already use “a bit” / “a little”.
- **Questions.** One in five advised comments ends with a question
  (“What would that look like here?”), plus question variants in the bank.
- **Length variance.** Long variants (45–60 words) for thesis, evidence,
  conclusion, topic sentence and paragraph focus; short mechanical notes stay
  under 12 words.
- **No contractions.** The reviewers never use them; neither do we.
- **Banned vocabulary.** `delve`, `moreover`, `furthermore`, `crucial`,
  `comprehensive`, `nuanced`, `tapestry`, `underscore`, `pivotal`, `leverage`,
  `robust`, `seamless`, `holistic`, `foster`, `navigate`, `realm`, `landscape`,
  `it is important to note` — rejected by the style guard.
- **Labels** carry the category, then a colon, exactly as the reviewers do.

## Testing against GPTZero

The Studio's result panel has **Copy all comments** and **Copy endnote**. They
copy plain text in paste-ready form:

```
1. THESIS STATEMENT: "…quoted sentence…"
The thesis states a position but does not show the road ahead. …
```

Paste that block into the detector. Comments are individually separable by the
numbered lines, so you can also isolate the ones that flag.

## Honest limits

- GPTZero has no public API, so this repository cannot score its own output.
  The corpus statistics are a proxy, not the detector.
- Deterministic templates cannot reproduce the content-specific naming that
  makes the human comments strong (“the records on antibiotic stewardship”,
  “the word dramatically”). The next step is retrieval: pick a reviewer comment
  with the same rhetorical move from `voice_corpus.json` and graft the student's
  specifics into it, rather than choosing a template.
- Until a batch is tested and reported, no anti-detection claim can be made.
  The loop is: generate → copy → test → report which items flag → adjust.
