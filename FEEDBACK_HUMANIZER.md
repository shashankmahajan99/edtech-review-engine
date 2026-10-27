# Guarded Feedback Humanizer (`engine/feedback_humanizer.py`)

This document describes the architecture, pinned prompt/sampling contracts, and deterministic preservation guards for the optional local feedback rewriter (`TS_HUMANIZER=local`).

## Architecture & Loopback Transport

- `engine/feedback_humanizer.py` is an optional loopback-only transport (`http://127.0.0.1`, `http://localhost`, or `http://[::1]`) activated only when `TS_HUMANIZER=local`.
- When `TS_HUMANIZER=off` (default), the review pipeline runs 100% offline using the deterministic composer (`engine/review/persona.py`), asymmetric endnote generator (`engine/review/endnote.py`), and 26-pattern scrubber (`engine/review/anti_ai_patterns.py`).

## Pinned Upstream & Recommended Sampling Profiles

### 1. Pinned Completion & Instruct Contracts (`engine/feedback_humanizer.py`)
To preserve strict backward compatibility with `tests/test_feedback_humanizer.py`:
- **Completion provider (`provider="completion"`, model `thinkingstorm-humanizer`):**
  - Prompt format file: `vendor/humanizer/prompt_format.json`
  - Pinned SHA-256 prefix (`PROMPT_FINGERPRINT`): `cc51d66b4c593fbe`
  - Pinned payload parameters: `temperature=1.0`, `top_p=0.95`, `top_k=0`, `min_p=0`, `repeat_penalty=1.0`
- **Instruct provider (`provider="instruct"`, model `thinkingstorm-editor`):**
  - Prompt file: `vendor/humanizer/editor_prompt.txt`
  - Pass 1 parameters: `temperature=0.72`, `top_p=0.92`, `enable_thinking=False`
  - Retry parameters: `temperature=0.35`, `top_p=0.90`, `enable_thinking=False`

### 2. High-Entropy Anti-Detector Local Profile (Reference / Custom Checkpoints)
When benchmarking unconstrained local GGUF checkpoints outside the pinned completion transport, use the anti-detector sampling profile:
- `temperature=0.92`
- `min_p=0.08`
- `top_p=0.98`
- `repeat_penalty=1.15`
- `presence_penalty=0.15`

## Deterministic Fact Masking & Post-Filter (`engine/review/humanization.py`)

Before any feedback passage is sent to the rewriter:
1. `mask_facts()` replaces all quoted student spans (`“...”`, `"..."`, `‘...’`), URLs (`https://knowledge.thinkingstorm.com/...`), dates (`15 October 2026`), numbers/units, and proper names with opaque `HZ<nonce>X<idx>Z` tokens.
2. `mla_date_numeric` and `apa_date_numeric` comments bypass rewriting altogether so current and suggested date formats can never be swapped.
3. `validate_rewrite()` verifies that every `HZ<nonce>X<idx>Z` placeholder is returned exactly once, expands any contractions outside quotes, runs `scrub_ai_tells(candidate, seed=nonce)` and `audit_ai_tells(candidate)`, and rejects any candidate that alters negations, conditionals, uncertainty modals, numeric facts, or advice direction.
