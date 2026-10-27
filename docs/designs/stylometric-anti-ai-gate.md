# Stylometric Humanizer and Anti-AI Gate for ThinkingStorm v2

## Problem and User Outcome

Supervised AI-detection classifiers (RoBERTa, DeBERTa, and GPTZero perplexity/burstiness models) flag generated feedback deliverables due to low variance in sentence length, predictable opener structures, copula avoidance, and repetitive n-grams common in template-based generation.

The objective is to implement an end-to-end local stylometric humanizer and anti-AI gate directly in the deterministic offline review engine (`engine/review/`). This eliminates AI-detector flags across both margin comments and closing endnote letters while strictly preserving offline determinism, exact student quoted text, and Word deliverable typography contracts.

---

## Architectural Design

### 1. `engine/review/anti_ai_patterns.py` (26-Pattern Structural Scrubber & Auditor)

A deterministic regex transformation module operating on generated feedback prose:
- **Quote & URL Protection**: Masks text inside double quotes (`"..."`), typographic quotes (`“...”`, `‘...’`), and `https://knowledge.thinkingstorm.com/` URLs with nonces (`__QUOTE_NONCE_X__`) before any transformation. Unpaired ASCII apostrophes (`'`) are treated as word apostrophes (contractions), never as quote boundaries.
- **`scrub_ai_tells(text: str, seed: int = 0) -> str`**:
  Applies the 26 structural and vocabulary patterns derived from Wikipedia/blader anti-AI practices and `docs/ANTI_AI_PRACTICES.md`:
  1. *Pattern 1 ("Not only X, but Y")*: `not only ..., but (also)?` -> direct assertion.
  2. *Pattern 2 ("A testament to")*: `stands? as a testament to` -> `reflects` / `shows`.
  3. *Pattern 3 ("Tapestry / Mosaic")*: `(rich|complex|multifaceted)?\s*tapestry of` -> `range of` / `collection of`.
  4. *Pattern 4 (Staged run-ups)*: Strips leading `"Here's the thing:"`, `"At its core,"`, `"Let's dive in"`, `"Honestly,"`.
  5. *Pattern 5 ("Beacon of")*: `beacon of (hope|light|clarity)` -> `guide for`.
  6. *Pattern 6 ("Paramount importance")*: `is of paramount importance` -> `is critical` / `is essential`.
  7. *Pattern 7 ("Crucial / Vital role")*: `plays? a (crucial|vital|pivotal) role in` -> `directly helps` / `is essential to`.
  8. *Pattern 8 ("Underscores / Highlights")*: `underscores the (importance|need) for` -> `shows why you need`.
  9. *Pattern 9 (Stacked qualifiers)*: `(could potentially|might possibly|may arguably)` -> `can` / `might`.
  10. *Pattern 10 ("Delve / Diving deep")*: `delv(e|es|ing|ed) into` -> `examin(e|es|ing|ed)` / `look(s|ing|ed) into`.
  11. *Pattern 11 ("In today's fast-paced")*: `in today's (fast-paced|modern|interconnected) world` -> `today`.
  12. *Pattern 12 ("Moreover / Furthermore")*: Leading `(Moreover|Furthermore|Additionally),?\s*` -> `Also, ` / `In addition, `.
  13. *Pattern 13 ("In conclusion")*: Leading `(In conclusion|To summarize),?\s*` -> `To close, `.
  14. *Pattern 14 ("It is important to note")*: `(It is (important|crucial|worth) (to note|noting) that)\s*` -> `Note that `.
  15. *Pattern 15 (Shallow `-ing` riders)*: Strips trailing participial padding (`,\s*(highlighting|underscoring|showcasing|demonstrating)\s+(how|that|the need).*$`).
  16. *Pattern 16 ("Interplay / Dynamic interplay")*: `(dynamic )?interplay between` -> `relationship between`.
  17. *Pattern 17 ("Fostering / Fosters")*: `foster(s|ing)?` -> `build(s|ing)?` / `support(s|ing)?`.
  18. *Pattern 18 (Copula avoidance)*: `(serves as|functions as|stands as)\s+a\s+` -> `is a `.
  19. *Pattern 19 ("Embarking on a journey")*: `embark(s|ing|ed)? on` -> `start(s|ing|ed)?` / `begin(s|ing|ed)?`.
  20. *Pattern 20 ("Nuanced understanding")*: `nuanced (understanding|perspective|view)` -> `detailed understanding`.
  21. *Pattern 21 ("Holistic approach")*: `holistic approach` -> `complete approach`.
  22. *Pattern 22 ("Seamlessly integrates")*: `seamlessly (integrates|connects)` -> `integrates` / `links`.
  23. *Pattern 23 ("Navigating the complexities")*: `navigat(e|es|ing) the complexities of` -> `working through`.
  24. *Pattern 24 ("Sheds light on")*: `sheds light on` -> `explains` / `clarifies`.
  25. *Pattern 25 (Document meta-reference)*: `this (essay|paper|document) (attempts|seeks|aims) to` -> `you aim to`.
  26. *Pattern 26 (Contraction injection)*:
      Injects natural contractions outside protected quotes using deterministic hash:
      `(int(hashlib.sha1(f"{seed}:{idx}".encode()).hexdigest(), 16) % 100) < 70`:
      `do not` -> `don't`, `is not` -> `isn't`, `cannot` -> `can't`, `you will` -> `you'll`, `it is` -> `it's`.
- **`audit_ai_tells(text: str) -> list[str]`**: Scans unquoted text and returns any matches against the 26 pattern definitions.

---

### 2. `tools/mine_voice_corpus.py` & `style_corpus/voice_profile.json`

- Mines the 25 verified human-reviewed documents (307 comments) to compute:
  - Sentence length quantiles: `p10`, `p25`, `p50`, `p75`, `p90`.
  - Target Coefficient of Variation: `target_cv = 0.45` (human baseline standard deviation / mean).
  - Categorizes exemplar openers into **6 Opener Archetypes** via regex classifier:
    1. `imperative_quote`: `^(Cut|Replace|Move|Delete|Trim|Omit|Drop|Swap)\b.*["“]`
    2. `socratic_check`: `^(Why|Which|How|What|Where|Could)\b.*\?`
    3. `contrastive_claim`: `^(You open with|Although|While|Whereas|Even though|You state)\b`
    4. `conditional_fix`: `^(If you want|When you revise|Should you)\b`
    5. `fragment_diagnosis`: `^[A-Z][a-z]+(?:\s+[a-z]+){0,4}[.:]\s+[A-Z]`
    6. `reader_anchor`: `^(A reader|The reader|After|Without)\b`
  - Saves distribution metrics and archetype seed lists to `style_corpus/voice_profile.json`.

---

### 3. `engine/review/persona.py` (Cross-Comment Burstiness & Entropy Controller)

Upgrades `CommentComposer` and `compose_all` to operate statefully across the sequence of selected comments `[c_0, c_1, ..., c_n]`:
- **Stateful Cadence Oscillation**:
  Maintains `prev_len: int` and `prev_archetype: str`.
  When scoring candidate templates for a finding:
  ```python
  score = 0.0
  # Opener diversity:
  if candidate_archetype != prev_archetype:
      score += 3.0
  if candidate_opener_bigram not in recent_openers:
      score += 2.0
  # Length burstiness delta:
  if abs(candidate_len - prev_len) >= 10:
      score += 2.5
  ```
  If variants allow, candidates with higher scores are chosen. If a rule has limited variants, the composer falls back gracefully to the best available candidate without discarding diagnostic advice.
- **Sub-Greedy Synonym Slot Selection**:
  High-frequency editorial verbs/nouns (`[tighten | sharpen | narrow | pin down]`, `[claim | assertion | point | argument]`) selected deterministically using `sha1(fingerprint | rule | pos)` to reduce 5-gram repetition to 0%.
- Runs `scrub_ai_tells(body, seed)` on every composed comment.

---

### 4. `engine/review/endnote.py` (Asymmetric Endnote Synthesis)

- **Asymmetric Section Sizing**:
  Calibrates section word counts to guarantee satisfying `validate.py` minimum words (`60/90/120`):
  - Priority 1: 50–65 words.
  - Priority 2: 35–45 words.
  - Priority 3: 40–55 words.
  Total words exceed 100 words (1 area), 140 words (2 areas), and 180 words (3 areas).
- **Sentence Burstiness**:
  Constructs priority blocks with at least one short sentence (`<= 8` words) and one multi-clause sentence (`>= 22` words).
- **Fact-Grounded Quotes**:
  Extracts specific quoted excerpts from `finding.quote` into the priority discussion.
- Runs `scrub_ai_tells(body, seed)` over endnote narrative paragraphs, keeping greeting, headings, and signature intact.

---

### 5. `engine/review/validate.py` & `cli.py` (Independent Release Gate)

- **Pure Read-Only Verification**:
  `validate.py` never alters documents or in-memory text. It only inspects the output `.docx` OpenXML package.
- **Metrics Computation**:
  Computes Sentence Length Coefficient of Variation:
  `cv = std_dev / mean` across comment bodies and endnote paragraphs.
- **Gate Enforcement**:
  - Rejects comments with banned words (`banned_hits`).
  - Verifies comments remain within 6–95 words and end with terminal punctuation.
  - Verifies endnotes satisfy minimum word thresholds (60/90/120 words).
  - Fails closed on any manuscript text drift or missing OpenXML parts.

---

## Invariants and Hard Constraints

1. **Air-Gapped Determinism**: 100% offline; zero network calls or external LLM dependencies in rules mode.
2. **Reproducibility**: Every stochastic choice seeded by `sha1(fingerprint | rule | pos)`.
3. **Student Text Preservation**: Text inside student quotes (`"..."`, `“...”`, `‘...’`) is strictly protected and never altered.
4. **Release Gate Integrity**: Native OpenXML structure, comment bounds (6-95 words), endnote typography (TNR 12pt #FF0000) remain strictly verified.
5. **No Mutating Validators**: Verification logic remains strictly read-only.

---

## Verification Gate

1. Unit tests in `tests/test_anti_ai.py` covering:
   - Pattern scrubber and auditor functionality across all 26 tells.
   - Nonce protection of student quotes and URLs.
   - Cross-comment burstiness and opener diversity.
   - 100% byte-identical reproducibility on fixtures.
2. Full unittest discovery: `python -m unittest discover -s tests -v` (all tests passing).
3. CLI selftest: `python -m engine.review.cli selftest --fixtures tests/fixtures`.
