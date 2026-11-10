# Workflow: product

Use for a complete product, next wave or PRD feature. Resolve `scope`, `interaction`, `destination` and `profile` before mutation. Default automatic profile is `lean`; direct skill invocation remains `manual-classic`.

## Start once

1. Run `harness.py doctor`, validate the PRD and synchronize tasks.
2. Run `harness.py prepare <first-task>` for the first ready task.
3. Apply the returned risk decision and budget gate.
4. For autonomous GitHub, create one Orca worktree and visible worker session for the selected delivery scope before code changes.

## Per feature

1. Generate a missing spec and plan with `spec-writer` under the active profile.
2. Implement with one writer in the assigned checkout.
3. Run the profile validation: `smoke` for lean, exhaustive phase and feature validation for strict.
4. Commit compact semantic units. In lean, prefer one feature commit and split only when rollback value is clear.
5. Lean low-risk work skips independent spec and code reviewers. Strict work reviews both. High-risk lean work is elevated to strict before implementation.
6. Run `harness.py checkpoint --task <id> --evidence <receipt>` and select the next dependency-ready task.
7. Run `harness.py prepare <next-task>` to create the next compact packet. Reuse the recorded product worktree instead of launching another one.

## Delivery

- Lean product or wave: keep the worktree for the scope, run `full` quality and `final-qa`, then open one cumulative PR.
- Strict: feature-level PRs and reviews are allowed when configured, but reuse isolation safely when the branch strategy permits it.
- Manual classic: follow the preserved G1 to G4 contract and user approvals.
- GitHub merges always use merge commit after green CI and the required review.
- Local-only work never mutates Git.

Call `harness.py finish` only when the selected scope is merged, completed locally, blocked, failed or cancelled. Cleanup only after confirmed merge, merge SHA and clean worktree evidence.

Stop on a human gate, budget stop, missing authority, invalid state, unrecoverable failure or completed scope.
