# Harness operating manual

## Purpose

Operate product work with progressive context, explicit authority, recoverable state and proportionate evidence. Do not load the whole harness.

## Request resolution

Resolve `scope`, `interaction`, `destination` and `profile`.

- Direct skill use defaults to `manual-classic`.
- Autonomous product work defaults to `lean`.
- `strict` is explicit or required by high risk.
- No explicit GitHub request means local destination.

Read only the selected workflow, skill entrypoint, profile references and current task context.

## Runtime cycle

1. Run `python .harness/scripts/harness.py doctor` once at the start.
2. Select a dependency-ready task.
3. Run `harness.py prepare` to apply the budget and risk gates, create a compact packet and ensure required isolation.
4. Execute the selected skill and profile.
5. Run compact computational quality before semantic review.
6. Run `harness.py checkpoint` after a feature. Keep the active delivery worktree in lean.
7. Prepare the next ready feature or run final QA when the selected scope ends.
8. Run `harness.py finish` once when the scope is merged, completed locally or terminated.

## Roles

The orchestrator coordinates and never writes product code. A single implementer writes inside each checkout. Spec authors write only under `.planning`. QA reviewers are read-only. Human gates override every profile.

## State and evidence

JSON is authoritative. `progress.md` is generated on demand. Store hashes, paths, statuses and compact receipts, not full prompts, diffs or command logs. Full logs live under `.harness/runtime/logs/` and are opened only for a specific need.

A compact packet includes the control root because `.harness` and `.planning` are local-only and are not copied into a Git worktree. The worker writes product code in the returned worktree path while the orchestrator owns local planning and state in the control root.

## Completion

Local completion requires the active quality profile. GitHub completion requires a confirmed merge SHA. Product completion in lean requires the final `full` quality profile and `final-qa`. Blocked or unverifiable worktrees are preserved.
