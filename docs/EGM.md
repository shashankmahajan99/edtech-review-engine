# Elephant-Goldfish Model (EGM) in this repository

EGM is Google's open-source **spec-driven development plugin** for AI coding
agents: a deep-context "Elephant" session drafts a design specification, and
isolated zero-context "Goldfish" reviewers stress-test it before code is written.
It is a workflow, not a model — nothing here runs inference, downloads weights,
or changes the review engine's offline behaviour.

- Upstream: https://github.com/google/elephant-goldfish-model
- Vendored at: `vendor/elephant-goldfish-model` (commit `3d0b348`, `egm` v0.1.0)
- License: Apache-2.0 (see the `LICENSE` in that directory)
- Not an officially supported Google product

## Why vendored rather than marketplace-installed

The plugin ships Claude Code and Codex marketplace manifests, which this
harness does not consume. Its skills are plain `SKILL.md` files, so any agent can
read and follow them directly. The vendored copy keeps `skills/`, `agents/`,
`resources/`, `docs/` and the manifests; the upstream marketing site, tests and
CI were dropped.

## DeepSeek Harness plugin

`plugins/dsh-egm-skills` is a Host-only DeepSeek Harness bundle that registers the
seven EGM skills with the Harness `skills` service. It owns copies of `SKILL.md`,
`docs/`, `agents/`, `resources/` and the Apache-2.0 LICENSE, so the skills resolve
their relative references inside the package. `${CLAUDE_PLUGIN_ROOT}` in the
upstream skill text is rewritten to `../..` for this layout.

Installed in the desktop profile as `include:dsh-egm-skills`; after installation
the skills appear in the catalog as `egm-brainstorm`, `egm-draft`, `egm-review`,
`egm-review-loop`, `egm-resolve`, `egm-drift-report` and `egm-bootstrap`.

Reinstall or move it with:

```
plugin_manager install_bundle target=C:\Users\shashank\edtech-review-engine\plugins\dsh-egm-skills
```

The bundle runs no model; it only hands instruction bodies to the agent.

## Using it here

Design documents live in `docs/designs/` (see the README there). Ask the agent to
follow a skill explicitly:

```
Read vendor/elephant-goldfish-model/skills/egm_brainstorm/SKILL.md and run it
for: <feature idea>. Write only the concept brief.
```

```
Read vendor/elephant-goldfish-model/skills/egm_draft/SKILL.md and turn the
concept brief into docs/designs/<feature>.md.
```

```
Read vendor/elephant-goldfish-model/skills/egm_review/SKILL.md and review
docs/designs/<feature>.md with the Goldfish reviewers in
vendor/elephant-goldfish-model/agents/.
```

| Skill | File | Purpose |
| --- | --- | --- |
| Brainstorm | `skills/egm_brainstorm/SKILL.md` | zero-doc ideation, Goldfish shootdown |
| Draft | `skills/egm_draft/SKILL.md` | section-by-section design spec |
| Review | `skills/egm_review/SKILL.md` | Zoom Out → Comprehension → Critic → Readiness |
| Review loop | `skills/egm_review_loop/SKILL.md` | concurrent review dispatch |
| Resolve | `skills/egm_resolve/SKILL.md` | triage and patch review findings |
| Drift report | `skills/egm_drift_report/SKILL.md` | spec-vs-code divergence |
| Bootstrap | `skills/egm_bootstrap/SKILL.md` | codebase documentation |

Goldfish personas (Design Critic, Naive Reader, Tech Lead, Codebase Auditor,
Structural Validator, Style Editor, Zoom Out Architect) are in
`vendor/elephant-goldfish-model/agents/`.

If you use Claude Code or Codex elsewhere, the upstream marketplace commands
still work; the vendored copy is independent.

## Boundaries

- EGM applies to **development** of this repository, not to its runtime. The
  review pipeline remains deterministic and offline; do not add model calls to
  `engine/` because a design doc suggests it.
- Design docs are proposals. Approval and implementation remain human decisions.
- The vendored `AGENTS.md` inside `vendor/elephant-goldfish-model` governs work
  on EGM itself; it does not change this repository's rules.
