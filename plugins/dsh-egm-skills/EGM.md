# dsh-egm-skills (DeepSeek Harness EGM Plugin)

## Overview

A Host-only DeepSeek Harness bundle that publishes the seven
Elephant-Goldfish Model (EGM) skills to the Harness skill catalog. `index.js` is
the entire executable surface: it reads the package's `skills/<dir>/SKILL.md`
bodies from disk once at apply time and hands them to the Harness `skills`
service. It runs no model, makes no network calls and adds no tools — it is a
pure content registrar, so it cannot change the review engine's deterministic,
offline runtime.

Packaging facts:

- `package.json` declares `"type": "module"`, exports `.` → `./index.js`,
  `./locale/*.json`, `./icon` (→ `icon.svg`), points `dsh.bundle.patch` at
  `cordis.patch.yml`, and whitelists `files`: `index.js`, `cordis.patch.yml`,
  `locale/*.json`, `icon.svg`, `skills/**`, `docs/**`, `agents/**`,
  `resources/**`, `LICENSE` (`README.md` ships by npm default).
- `cordis.patch.yml` only inserts the entry
  `{ id: dsh-egm-skills, name: dsh-egm-skills, config: {} }` — no configuration
  keys are read by `index.js`, and there is no schema to validate.
- [locale/en.json](locale/en.json) supplies catalog `meta.title` /
  `meta.description`.
- Skill bodies are copies of
  [vendor/elephant-goldfish-model/skills](../../vendor/elephant-goldfish-model/skills)
  at upstream commit `3d0b348`, not a byte-identical mirror. Every `SKILL.md`
  rewrites `${CLAUDE_PLUGIN_ROOT}/docs/claude.md` to `../../docs/claude.md`
  ([docs/EGM.md](../../docs/EGM.md) documents that rewrite). Apart from that
  rewrite and one extra trailing blank line, `egm_brainstorm`,
  `egm_drift_report` and `egm_resolve` match the vendor copy exactly. Four
  bodies also carry UTF-8-read-as-Latin-1 mojibake that the vendor copy does not
  have: `egm_bootstrap` has three damaged template emoji in its "Templates"
  headings (`ðŸ“„` where the vendor copy has `📄`); `egm_review` and
  `egm_review_loop` have the three severity emoji in their legends
  (`ðŸ”´`/`ðŸŸ¡`/`ðŸŸ¢` for `🔴`/`🟡`/`🟢`), and `egm_review` additionally has
  `Stages 5â€“8` for `Stages 5–8`; `egm_draft` has two en dashes as `â€“`
  (`Steps 2â€“5`, `2â€“3`). The registered body is the package copy under
  [skills/](skills/), which is what the catalog serves; `docs/EGM.md` separately
  tells agents to read the vendor copy, so a skill edit must be made in both
  trees.
- Each skill directory also ships `TEST.md` and `test_scenarios.yaml` from
  upstream. They are packaged (`skills/**`) but never read by `index.js` and
  never registered.
- The plugin also owns [docs/](docs/), [agents/](agents/),
  [resources/](resources/) and the Apache-2.0 `LICENSE` so relative references
  inside the skill text resolve against the package: every body links
  `../../docs/codex.md`, and the package adds `docs/claude.md`, `docs/harnesses.md`
  and the reference documents the skills name (`references/worker-return.schema.json`
  in `egm_bootstrap`, `references/design_doc.md` in `egm_draft`).

## Problem & Scope

- EGM is vendored, but the Harness only sees skills registered with its
  `skills` service, so the seven bodies need a bundle that publishes them.
- `plugins/dsh-egm-skills` is that bundle: a Host-only registrar that hands
  `skills/<dir>/SKILL.md` content and the reference trees it points at to the
  Harness.
- In scope: the seven skills, their `whenToUse` text, `docs/`, `agents/`,
  `resources/`, `locale/`, and the Apache-2.0 licence.
- Out of scope: executing a skill, model invocation, tool registration, and any
  change to review-engine behaviour.

## Goals & Non-Goals

- Goal: the seven EGM skills appear in the Harness catalog under stable
  kebab-case names.
- Goal: each skill resolves relative references inside the installed package via
  `resourceBase`, never via `process.cwd()`.
- Goal: stay inert — no network, no model, no timers, no tool registration, no
  writes at apply time.
- Non-goal: detecting drift against
  `vendor/elephant-goldfish-model/skills`; the copies are maintained by hand
  (see Invariants).
- Non-goal: layout discovery beyond the single Cordis bundle patch.

## Alternatives Considered

- Installing the upstream marketplace plugin: rejected — it ships Claude Code
  and Codex manifests this Harness does not consume.
- Pointing `resourceBase` at the vendor tree instead of copying: rejected
  implicitly; installed bundles are self-contained, so the package ships its own
  `skills/`, `docs/`, `agents/`, `resources/`.
- Reading bodies from `vendor/` at apply time: not done; `readFileSync` reads
  only `join(here, 'skills', dir)`.
- Generating the skill table from `docs/EGM.md`: not implemented; both lists are
  hand-maintained.

## Risks & Mitigations

- Missing body is silent: `catch → continue` drops that skill with no error and
  no registration (so no `resourceBase` either), leaving the catalog short by
  one entry. Mitigation: the seven-file check in Verification.
- Two divergent skill copies: the package copy carries the `../../docs/claude.md`
  rewrite and, in four bodies, mojibake (three emoji in `egm_bootstrap`,
  `egm_review` and `egm_review_loop`; three en dashes across `egm_review` and
  `egm_draft`), while `docs/EGM.md` points agents at the vendor copy. Mitigation:
  edit both, and treat the package copy as what the catalog serves.
- `invocation.modelInvocable: true` overrides the
  `disable-model-invocation: true` frontmatter present in all seven bodies, so
  an agent may auto-invoke a skill its text marks manual.
- The bundle records no upstream revision beyond a source comment (`3d0b348`),
  so a vendor update cannot be detected from the package.

## Interface

### Module exports (`index.js`)

- `export const inject = ['skills']` — the plugin refuses to load unless the
  Harness `skills` service is available.
- `export function apply(ctx)` — the Cordis plugin entry point.
- Not exported: `SKILLS` (the internal registry table), the `here` base
  directory resolved with `fileURLToPath(new URL('.', import.meta.url))`.

### Registered skills (seven)

Each entry of `SKILLS` has `{ name, dir, description, whenToUse }`, and the
registration passes `content` read from `skills/<dir>/SKILL.md`:

| Skill name | Source directory | Purpose (from `whenToUse`) |
| --- | --- | --- |
| `egm-brainstorm` | [`skills/egm_brainstorm`](skills/egm_brainstorm/SKILL.md) | Attack a vague idea from several reviewer perspectives before committing to a design. |
| `egm-draft` | [`skills/egm_draft`](skills/egm_draft/SKILL.md) | Turn a settled concept into a written spec under `docs/designs/`. |
| `egm-review` | [`skills/egm_review`](skills/egm_review/SKILL.md) | Adversarial, zero-context review of an existing design document. |
| `egm-review-loop` | [`skills/egm_review_loop`](skills/egm_review_loop/SKILL.md) | Dispatch several independent reviewers in parallel rather than one pass. |
| `egm-resolve` | [`skills/egm_resolve`](skills/egm_resolve/SKILL.md) | Accept, reject or patch review findings in the spec. |
| `egm-drift-report` | [`skills/egm_drift_report`](skills/egm_drift_report/SKILL.md) | Detect where implementation moved away from an approved design. |
| `egm-bootstrap` | [`skills/egm_bootstrap`](skills/egm_bootstrap/SKILL.md) | Document an undocumented area of the repository before design work. |

### Registration payload passed to `ctx.skills.register`

```js
{
  name, description, whenToUse, content,
  source: 'custom',
  provider: 'egm',
  resourceBase: { kind: 'directory', path: dir },
  invocation: { modelInvocable: true, userInvocable: true },
}
```

`resourceBase` is the absolute `skills/<dir>` path, which is what lets a skill
resolve its own relative references (for example the
[`skills/egm_bootstrap/SKILL.md`](skills/egm_bootstrap/SKILL.md) link to
`references/worker-return.schema.json`).

- Sibling contracts: [repository EGM guide](../../docs/EGM.md),
  [vendored upstream skills](../../vendor/elephant-goldfish-model/skills/),
  [bundle README](README.md).

## Invariants

- Skill names are kebab-case; the Harness registry requires it, while the
  on-disk directories keep the upstream snake_case (`egm_bootstrap`, …). The
  `name` / `dir` pair is the only place the two spellings meet.
- `inject = ['skills']` must stay exact: registering before the service exists
  is not attempted, and there is no fallback path.
- Every registration is wrapped in `ctx.effect(...)` so disabling or unloading
  the plugin disposes the registered skills; never call
  `ctx.skills.register` outside `ctx.effect`.
- A skill whose `SKILL.md` cannot be read is silently skipped (`catch` →
  `continue`) before any registration. Missing bodies degrade the catalog rather
  than failing the plugin load, so a renamed directory produces a missing skill
  with no error.
- The seven-entry `SKILLS` table is the contract with the repository docs: the
  `name` list in [docs/EGM.md](../../docs/EGM.md) and the skill table in that
  file's "Using it here" section. That table lists the same seven names with
  bare `skills/egm_*/SKILL.md` paths and its earlier instructions send agents to
  the vendor tree, while `index.js` registers the package copies, so adding or
  renaming a skill means updating the table here, both copies of the body, and
  that doc. Nothing detects the mismatch.
- `invocation.modelInvocable` is `true` for every skill even though all seven
  `SKILL.md` bodies declare `disable-model-invocation: true`. The frontmatter is
  prose for the agent; the registration flag is what the Harness enforces, so
  every skill is model-invocable despite its own text.
- No model calls, no HTTP, no timers, no tool registration: the plugin must stay
  purely declarative so EGM remains a development workflow and cannot leak
  inference into the runtime.
- Path resolution is relative to the installed package directory
  (`import.meta.url`), never to `process.cwd()`, so the bundle works from any
  working directory.

## Side Effects

- Disk reads: one synchronous `readFileSync` per skill of
  `skills/<dir>/SKILL.md` at apply time (seven reads). No writes, no temporary
  files, no cache on disk.
- Harness state: adds seven entries to the `skills` service catalog with
  `provider: 'egm'` and `source: 'custom'`; disposal by the effect removes them.
- Filesystem paths exposed to the agent: the skill's own directory via
  `resourceBase`, which widens relative reads to `../../docs/` (the package's
  `docs/`, since the rewrite climbs two levels) and to the skill's own
  `references/`/`TEST.md` files.
- No stdout logging, no environment variables, no credentials, no network, and
  no writes outside the Harness profile.

## Verification

- Run: `python -m unittest discover -s tests`
- The Python suite does not import this bundle (it is JavaScript); use it to
  confirm the repository around the plugin still passes after any change.
- Structural check of the bundle itself: run
  `node --check plugins/dsh-egm-skills/index.js` for syntax, then confirm the
  registry resolves. Listing `plugins/dsh-egm-skills/skills/*/SKILL.md` (for
  example `Get-ChildItem plugins/dsh-egm-skills/skills/*/SKILL.md`) must return
  seven files, and each directory name must equal a `dir` in `SKILLS`. A missing
  or renamed body is skipped silently, leaving the catalog short.
- There is no automated drift check between the package copies and
  `vendor/elephant-goldfish-model/skills`; compare the two trees by hand after
  touching either. Expected differences are exactly one `docs/claude.md` path
  rewrite per body, one extra trailing blank line, and the mojibake listed in
  Overview (`egm_bootstrap`, `egm_review`, `egm_review_loop`, `egm_draft`).
