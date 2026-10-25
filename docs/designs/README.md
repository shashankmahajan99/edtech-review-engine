# Design documents

Specifications written with the [Elephant-Goldfish Model](../EGM.md) live here.

- One document per feature or architectural change: `docs/designs/<feature>.md`.
- Names are kebab-case and describe the change, not the ticket: `review-queue-batching.md`.
- The document is the contract: implementation is reviewed against it, and drift is
  reported by `vendor/elephant-goldfish-model/skills/egm_drift_report/SKILL.md`.
- Status is recorded in the document header (Draft / In review / Approved /
  Implemented / Superseded).

Nothing in this directory affects the runtime. It is written before code.
