# Profiles

A profile sets how much rigor a run applies. All profiles use the same [workflows](./workflows.md); they change how specs are reviewed, how much validation runs and when code is reviewed.

## Comparison

The values come from `.jotta/profiles/*.yaml`.

| Setting | `manual-classic` | `lean` | `strict` |
|---|---|---|---|
| Spec review | Manual, by the user | Only for high-risk work | Always |
| Validation | Per feature | `smoke` per feature | Per phase and per feature |
| Code review | Manual | Once, at the end | Per feature |
| Commits | Atomic | Compact and semantic | Compact and semantic |
| Worktree | When requested | Always for autonomous GitHub | Always for autonomous GitHub |
| Final QA | Manual | For the product | For the product |

- **manual-classic** keeps the original, detailed contracts: interviews, the human gates G1 to G4, plans and detailed validation. It is the compatibility path for the earlier workflow.
- **lean** is the autonomous default. It loads compact references, runs `smoke` checks per feature, skips per-feature reviewers for low-risk work and concentrates semantic review at the end of the scope.
- **strict** reuses the complete contracts with automation and reviews every spec and every feature.

## Selection

1. A profile the user names explicitly always wins.
2. Invoking a skill directly defaults to `manual-classic`.
3. Autonomous product work defaults to `lean`.
4. `strict` is used when requested or when risk requires it.

## Risk elevation

`jotta prepare` classifies the task text, the matching PRD excerpt and the feature spec. When they mention a high-risk topic, such as authentication, authorization, payments, billing, secrets, security, schema migrations, personal data, permissions, production, infrastructure, public APIs or breaking changes, a `lean` request runs as `strict`. The context packet records both profiles and the matched terms under `risk`, and the implementer is routed to the high-risk model route.

## Quality per profile

`.jotta/config.yaml` maps profiles to the quality gates in `.jotta/sensors/computational/gates.json`.

| Moment | Lean | Final |
|---|---|---|
| After each feature | `smoke` | |
| After each wave | `feature` | |
| Before delivery | | `full` and final QA |

An empty quality profile returns `skipped`, never a false pass.
