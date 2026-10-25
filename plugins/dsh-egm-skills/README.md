# dsh-egm-skills

DeepSeek Harness plugin that exposes the seven
[Elephant-Goldfish Model](https://github.com/google/elephant-goldfish-model)
skills to the Harness skill catalog.

EGM is Google's Apache-2.0 spec-driven development workflow: an "Elephant"
session drafts a design specification, and isolated zero-context "Goldfish"
reviewers attack it before code is written. The plugin registers the upstream
`SKILL.md` files; it runs no model and changes no runtime behaviour.

## Skills

| Name | Purpose |
| --- | --- |
| `egm-brainstorm` | multi-lens shootdown of an early concept |
| `egm-draft` | section-by-section design specification |
| `egm-review` | Zoom Out → Comprehension → Critic → Readiness |
| `egm-review-loop` | concurrent reviewer dispatch |
| `egm-resolve` | triage and patch review findings |
| `egm-drift-report` | spec-versus-code divergence |
| `egm-bootstrap` | bottom-up codebase documentation |

Skill bodies are copied from upstream commit `3d0b348` under
`skills/<name>/SKILL.md`; `resourceBase` points at that directory so relative
references resolve.

## Install

```
plugin_manager install_bundle target=C:\...\edtech-review-engine\plugins\dsh-egm-skills
```

## License

The bundled skill text is Apache-2.0, © Google LLC. Plugin packaging is original.
