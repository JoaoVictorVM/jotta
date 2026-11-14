# 0004: Merge pull requests with a merge commit

- Status: Accepted
- Date: 2026-11-14

## Context

Jotta asks agents for logical commits in Conventional Commits format: the `implement-feature` contract commits per phase, and the `commit-manager` skill plans commits before they are created and checks each message with the commit gate. Each commit is meant to be reviewed and reverted on its own. GitHub offers three ways to merge a pull request: merge commit, squash and rebase.

- A squash merge collapses those commits into one, so the history loses the units the agent was asked to produce and a partial revert becomes a manual job.
- A rebase merge rewrites the commits with new SHAs. The harness records the merge SHA as evidence that a feature is done, and a resumed run checks the existing pull request and commits before continuing, so rewritten history breaks that evidence.

## Decision

Pull requests are merged with a merge commit, and only after the required checks are green and the review required by the profile is approved.

- `jotta finish --status merged` records the merge commit SHA.
- Worktree and branch cleanup happens only after that SHA exists and the worktree is clean. Local branches are deleted with safe deletion.
- Squash and rebase merges count as failures in the evals.

## Alternatives

- **Squash.** Gives a short linear history, but discards the atomic commits and their messages. Rejected.
- **Rebase.** Keeps the commits but rewrites them, which invalidates recorded SHAs and evidence. Rejected.
- **Direct pushes to the default branch.** Skips CI and review. Rejected.

## Consequences

- The history shows each delivery as a merge with its atomic commits underneath, and `git log --first-parent` gives the delivery-level view.
- Any single commit can be reverted, and a whole delivery can be reverted through its merge commit.
- The history is less linear than with squash. That is the accepted cost.
- Projects whose own policy requires squash must change this rule in their installed harness. The evals will then flag the difference.
