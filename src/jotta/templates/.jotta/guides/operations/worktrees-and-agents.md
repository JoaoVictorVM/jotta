# Worktrees and agents

Agents, worktrees and Orca sessions are separate decisions.

- An agent is a role and context.
- A worktree isolates a writer and branch.
- An Orca session makes the selected model visible and controllable inside that worktree.

## Decision

Use an Orca worktree for every autonomous GitHub writer, simultaneous writers, risky refactors and explicitly isolated work. Use no worktree for local no-Git execution or ordinary read-only analysis. Supervised GitHub uses one when the task is large, risky, long-running, the main checkout is dirty or the user requests it.

One writer owns each worktree. Foundation work and writers touching the same central files run sequentially. Read-only review normally uses no extra worktree.

## Lifecycle

1. Inspect Git state, base, existing worktrees and branch collisions.
2. Load the version-matched Orca CLI guide.
3. Create an Orca-managed worktree and launch the selected agent with the initial prompt. Use a terminal surface when visible terminal execution is requested.
4. Record the complete Orca worktree id, path, branch and agent handle in `current-run.json`.
5. Execute all writes, builds and tests inside that path.
6. Record meaningful status on the Orca worktree.
7. After a confirmed merge, verify the worktree is clean and has no unique unmerged work.
8. Close its terminals, remove the Orca worktree and delete the local branch only when safe. Remote deletion follows repository policy.

Never remove a blocked, dirty, unmerged or unverifiable worktree. Never fall back silently from required isolation to the main checkout.
