import { readFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'

export const inject = ['skills']

const here = fileURLToPath(new URL('.', import.meta.url))

// Mirrors vendor/elephant-goldfish-model/skills at commit 3d0b348.
// Names are kebab-case because the Harness skill registry requires it.
const SKILLS = [
  {
    name: 'egm-brainstorm',
    dir: 'egm_brainstorm',
    description:
      'Zero-document ideation with a multi-lens Goldfish shootdown swarm that stress-tests an early concept before any spec exists.',
    whenToUse:
      'Use when an idea is still vague and you want it attacked from several reviewer perspectives before committing to a design.',
  },
  {
    name: 'egm-draft',
    dir: 'egm_draft',
    description:
      'Iterative, section-by-section compiler that turns a concept brief into a markdown design specification.',
    whenToUse:
      'Use when a concept is settled enough to become a written spec under docs/designs/.',
  },
  {
    name: 'egm-review',
    dir: 'egm_review',
    description:
      'Goldfish review protocol: Zoom Out, Comprehension, Design Critique, Intermediate synthesis and Implementation Readiness.',
    whenToUse:
      'Use when a design document exists and needs adversarial, zero-context review before implementation.',
  },
  {
    name: 'egm-review-loop',
    dir: 'egm_review_loop',
    description:
      'Concurrent review dispatch engine that runs the Goldfish reviewers directly or hierarchically.',
    whenToUse:
      'Use when a review needs several independent reviewers dispatched in parallel rather than one pass.',
  },
  {
    name: 'egm-resolve',
    dir: 'egm_resolve',
    description:
      'Interactive triage of review findings with automated patch application for accepted items.',
    whenToUse:
      'Use after an EGM review produces findings that must be accepted, rejected or patched in the spec.',
  },
  {
    name: 'egm-drift-report',
    dir: 'egm_drift_report',
    description:
      'Sequential scan that reports divergence between checked-in design specs and the live code.',
    whenToUse:
      'Use when implementation may have moved away from an approved design document.',
  },
  {
    name: 'egm-bootstrap',
    dir: 'egm_bootstrap',
    description:
      'Recursive bottom-up codebase documentation generator that upserts sentinel blocks.',
    whenToUse:
      'Use when an undocumented area of the repository needs structured documentation before design work.',
  },
]

export function apply(ctx) {
  for (const skill of SKILLS) {
    const dir = join(here, 'skills', skill.dir)
    let content
    try {
      content = readFileSync(join(dir, 'SKILL.md'), 'utf8')
    } catch {
      continue
    }
    ctx.effect(() =>
      ctx.skills.register({
        name: skill.name,
        description: skill.description,
        whenToUse: skill.whenToUse,
        content,
        source: 'custom',
        provider: 'egm',
        resourceBase: { kind: 'directory', path: dir },
        invocation: { modelInvocable: true, userInvocable: true },
      }),
    )
  }
}
