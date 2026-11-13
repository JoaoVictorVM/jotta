# Workflows

Every request is routed to one of three workflows. The detailed instructions live in `.jotta/workflows/`; this page summarizes them.

## Resolving a request

Before changing anything, the agent resolves four dimensions:

| Dimension | Values | Default |
|---|---|---|
| Scope | Product, next wave, feature or change | Feature |
| Interaction | Supervised or autonomous | Depends on the request |
| Destination | Local or GitHub | Local; GitHub only when requested |
| Profile | `manual-classic`, `lean` or `strict` | See [profiles](./profiles.md) |

Local work never mutates Git. Autonomous GitHub work requires an Orca worktree and a visible worker session.

## Product

Use it for a complete product, the next wave or a PRD feature.

1. Run `jotta doctor`, validate the PRD and synchronize tasks with `jotta sync-tasks`.
2. Run `jotta prepare <task>` for the first dependency-ready task. It applies the budget gate and risk classification, writes a compact context packet and, for autonomous GitHub work, launches the Orca worktree.
3. For each feature: generate a missing spec and plan with `spec-writer`, implement with a single writer, run the profile's validation, commit, then run `jotta checkpoint` with the quality receipt and prepare the next ready task.
4. Deliver according to the profile. Lean keeps one worktree for the scope, runs the `full` quality profile and `final-qa`, then opens one cumulative pull request. Strict allows feature-level pull requests and reviews. Manual classic follows the G1 to G4 contract.
5. Run `jotta finish` when the scope is merged, completed locally, blocked, failed or cancelled. Cleanup requires a confirmed merge SHA and a clean worktree.

## Change

Use it for a bug, small adjustment, refactor, feature extension or product revision.

1. Classify the request and create only the minimum artifact under `.planning/changes/<slug>/`.
2. A bug needs reproduction, expected behavior and regression evidence. A small change needs an objective, exclusions and acceptance criteria. A new feature updates the PRD and follows the product workflow. A major change in product direction stops at a human gate.
3. Prepare, implement, validate and finish with the same rules as the product workflow.

## Quality

Use it for feature, wave, product or pull request validation.

1. Run the computational quality profile first with `jotta quality <profile>`. Full output goes to `.jotta/runtime/logs/`; the model receives a compact receipt.
2. If the checks pass and the profile requires no semantic review, stop there.
3. Create a `final-qa` reviewer only for a requested review, high-risk scope, wave or product review, or failing evidence that needs diagnosis.
4. The reviewer reports findings and never edits code. Fixes go back to an implementer and the failing checks run again.

## Roles

| Role | Writes | Responsibility |
|---|---|---|
| Orchestrator | Local planning and state | Selects work, applies profile, policy and isolation; never writes product code |
| Spec author | `.planning/` only | Writes specs and plans |
| Implementer | The assigned checkout | The only writer in its worktree |
| Reviewer and QA reviewer | Nothing | Read-only review with evidence |

Human gates override every profile. See [guides and sensors](./guides-and-sensors.md).
