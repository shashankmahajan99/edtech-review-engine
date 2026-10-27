# Local ThinkingStorm Reviewer (`--backend local`)

This document specifies the configuration, sampling profile, exemplar injection, and deterministic post-filtering for the guarded local manuscript reviewer in `engine/review/local_model.py`.

## Runtime Isolation & Air-Gapped Rules Guarantee

- `--backend rules` (the default deterministic pipeline in `engine/review/`) makes zero model or network calls and imports no external LLM SDKs.
- `--backend local` connects only to a loopback HTTP endpoint (`http://127.0.0.1`, `http://localhost`, or `http://[::1]`) configured via `TS_LOCAL_CONFIG` (default `output/local-model/config.json`). Remote origins are rejected.

## Anti-AI Sampling Profile

When running local generative review or unconstrained local editorial passes, sampling parameters are tuned to avoid greedy token predictability while preserving JSON validity:

| Parameter | Target Value | Purpose |
| :--- | :--- | :--- |
| `temperature` | `0.92` | Breaks greedy modal token sequences across sentences |
| `min_p` | `0.08` | Truncates low-probability tail tokens dynamically relative to top token |
| `top_p` | `0.98` | Retains natural lexical entropy in the nucleus |
| `repeat_penalty` | `1.15` | Penalizes repeated n-grams and stock transition frames |
| `presence_penalty` | `0.15` | Encourages varied verb and opener selection across comments |

## Exemplar Injection & Condensed 26 Anti-AI Rules

Each local review request injects retrieved human reviewer exemplars from `style_corpus/exemplars.json` (`output/local-model/examples.json`, excluding any exemplar from the same manuscript) alongside three core exemplar archetypes:

1. **THESIS STATEMENT (`janeen_REV_BY_TS_RaunakB_243347_1.docx`):**
   > Your thesis outlines your broad topic, but could be tighter. Make sure your thesis explicitly previews the major analytical points your body paragraphs will explore.
2. **ANALYSIS OF EVIDENCE (`janeen_REV_BY_TS_RaunakB_243347_1.docx`):**
   > The paragraph reports the evidence without explaining its relevance to the claim. Once you present these findings, elaborate on what the data proves and how it supports the main claim.
3. **SUBJECT-VERB AGREEMENT (`kiran_REV_BY_TS_RaunakB_243490_1.docx`):**
   > The subject and verb do not agree here, which makes the sentence sound awkward. Identify whether the subject is singular or plural, then match the verb to it.

### Condensed 26-Pattern Anti-AI Checklist

1. **No negative parallelisms:** Never write `"This is not just X, it is Y"` or `"Not only X, but also Y"`. State the direct diagnosis.
2. **No staged run-ups:** Never open with `"Here's the thing:"`, `"At its core,"`, `"Let's dive in"`, or `"Honestly,"`.
3. **No stacked qualifiers:** Replace `"could potentially"`, `"might possibly"`, `"may arguably"` with a single modal (`"can"`, `"might"`, `"may"`).
4. **No trailing participial `-ing` riders:** Never append `", highlighting how..."`, `", underscoring the need..."`, or `", showcasing that..."` at clause ends.
5. **No copula avoidance:** Use `"is"` or `"has"` instead of `"serves as"`, `"functions as"`, `"stands as"`, or `"boasts"`.
6. **No document meta-reference:** Address the student directly (`"you try to"`, `"your draft"`) instead of `"this essay attempts to"` or `"the paper seeks to"`.
7. **No banned AI discourse or vocabulary:** Never use `delve`, `tapestry`, `testament`, `beacon`, `paramount`, `crucial/vital/pivotal role`, `underscores`, `interplay`, `foster`, `embark on`, `nuanced`, `holistic`, `seamlessly`, `navigating the complexities`, `sheds light on`, `furthermore`, `moreover`, `additionally`, `notably`, `in conclusion`, or `it is worth noting`.

## Deterministic Post-Filter & Release Gate

Every comment and closing-letter paragraph returned by `engine/review/local_model.py` is passed through:
1. `scrub_ai_tells()` in `engine/review/anti_ai_patterns.py` (which masks quoted student substrings and `https://knowledge.thinkingstorm.com/` URLs first, strips any of the 26 patterns, and enforces the 0% contraction corpus standard).
2. `audit_ai_tells()` and `banned_hits()` in `engine/review/validate.py` before any `.docx` deliverable is released.
