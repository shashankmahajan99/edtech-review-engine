# Knowledge base integration (v2)

`knowledge/thinkingstorm_kb_v2.json` is the ThinkingStorm-aligned rule data
returned by the external model: 22 rhetorical moves, 88 comment patterns, 120
diagnostics, 80 sources and an endnote template. It is rule data, not a parser —
its own `publication_note` says so — so the deterministic analyser in
`engine/review/analysis.py` remains the detector.

Validate it at any time:

```
python tools/validate_kb.py
```

## What is wired in

| KB section | Use |
| --- | --- |
| `moves` / `patterns` | Added to the comment pool for **rhetorical** moves only (`thesis`, `introduction`, `abstract`, `evidence`, `analysis`, `statistics`, `transitions`, `topic_sentences`, `organization`, `conclusion`, `clarity`, `logic`, `genre`). Citation and mechanics moves keep the local rule-specific templates, because a move-level pattern can contradict the exact rule (an “indentation” line attached to a missing-instructor finding). |
| `banned_phrases` | Merged into `BANNED_PHRASES`; the style guard rejects any generated comment containing one. |
| `endnote_template` | Its greeting body and closing are used for half the documents (stable hash); the other half keeps the local variants so letters do not read identically. |
| `persona`, `anti_ai_rules` | Kept as the reference for voice and distribution targets; the composer already enforces the measurable ones (no contractions, hedges, questions, shape mix). |
| `sources`, `diagnostics`, `quality_gates` | Stored for provenance and future diagnostic wiring. The 120 diagnostics are not detection rules yet; mapping them onto the analyser would require evidence extractors the KB itself says it expects. |

## Slot policy

Patterns are filled only from facts present in the draft:

- `anchor` / `quote` — the exact anchored span, trimmed to 12 words;
- `topic` — the document title, only when it is eight words or fewer;
- `source` — a citation found in the paragraph, or the rule's detected source;
- `term` — the rule's detected word;
- `value` / `measure` — a number in the paragraph;
- `grammar_feature`, `style`, `genre`.

Keyword guessing was removed: it produced lines like “discusses occurs and
bacteria together”. Patterns needing `point`, `other_point`, `detail`, `claim`,
`work`, `device`, `theme`, `event`, `group` or `research_question` are skipped
rather than filled with a guess, exactly as the KB's own slot policy requires.

## Precedence

Local rule-specific templates come first, then KB patterns that use a verified
anchor/source/topic, then KB patterns with no draft detail. The corpus shape
rules (one-sentence notes, hedges, questions) still apply on top.

## Diagnostic coverage (120 ids)

`knowledge/diagnostic_map.json` maps every KB diagnostic to the analyser:

| Status | Count | Meaning |
| --- | --- | --- |
| `mapped` | 43 | a detected rule covers it; the comment carries the diagnostic id |
| `human_only` | 55 | the KB marks it semantic/external (plagiarism, fallacies, literary reading, source stance, annotation credibility, Chicago, cover letters, nursing) — never asserted offline |
| `no_rule` | 22 | a mechanical check the analyser does not implement yet (run-ons, articles, tense, punctuation sub-rules) |

42 analyser rules now emit a diagnostic id; the four without one are local
extras (`implausible_year`, `org_name_mismatch`, `para_filler`,
`para_monotone`). Every comment in the QA JSON carries `diagnostic`, and
`pipeline.comments` exposes it to the portal.

Report or rebuild:

```
python tools/report_diagnostic_coverage.py
python tools/build_diagnostic_map.py
```

`tests/test_diagnostics.py` asserts all 120 are classified, every mapped rule
exists, and the status counts stay honest.

## Tests

`tests/test_kb.py` validates the file, checks the 22/88/120/80 counts, verifies
the banned list merge, and asserts that no rendered pattern leaks a `{slot}` or a
contraction and that mechanics moves never take a KB pattern.
