---
name: product-orchestrator
description: Coordinate a PRD product, wave, feature or change through manual-classic, lean or strict execution, including state, budget, model routing, Orca worktrees, GitHub and final QA.
---

# Product Orchestrator

Read `.harness/AGENT-MANUAL.md`, the orchestrator role, permissions, current state and only the selected workflow.

## Resolve

Determine `scope`, `interaction`, `destination` and `profile`. Direct skill flows default to `manual-classic`; autonomous product execution defaults to `lean`; no explicit GitHub request defaults to local. High-risk prepared tasks require `strict` unless a human explicitly changes the risk policy.

## Coordinate

1. Run `doctor` once and synchronize PRD tasks when required.
2. Select dependency-ready work and run `harness.py prepare`.
3. Apply budget and model routing before creating a worker.
4. For required isolation, follow the worktree guide and Orca adapter. Do not dispatch the writer until the complete worktree id and launched agent handle are recorded.
5. Invoke `spec-writer` only when the current task lacks a valid spec.
6. Invoke `implement-feature` with the complete `HARNESS_RUN` envelope and prepared context receipt.
7. Lean low-risk work uses computational smoke evidence and defers semantic review to final QA. Strict work reviews every feature.
8. Merge only through the product workflow, then call `finish` and clean a verified worktree.
9. Run wave integration and product final QA at their boundaries.

Never implement product code. Stop on human gates, budget stop, missing authority, invalid state, repeated failure, cancellation or completed scope.
