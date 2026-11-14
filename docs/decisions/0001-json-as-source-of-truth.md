# 0001: Keep run state in JSON files

- Status: Accepted
- Date: 2026-11-14

## Context

Coding agents lose context. A conversation can be interrupted, compacted or continued by a different agent or provider, and the next session has to know which features are done, which run is active, which pull request is open and how much budget was spent. Markdown progress notes are easy for people to read but hard for a program to check: two agents can describe the same state in different words, and nothing stops a note from claiming a feature is merged without a merge SHA.

The harness also has to run in any project, offline, on Linux, macOS and Windows, with no service to install.

## Decision

The run state lives in JSON files under `.jotta/runtime/state/`: `current-run.json`, `tasks.json` and `usage.json`. They are the only source of truth.

- Only the `jotta` command writes them, through atomic writes (a temporary file followed by a rename).
- Transitions that need evidence enforce it. `finish --status merged` requires `--merge-sha`, and cleanup requires a clean worktree.
- Markdown files such as `progress.md` are generated projections for people and are never read back as state.
- A missing file means an empty default. The templates ship no state, and the runtime is ignored by Git.
- Task records are reconciled by feature ID when the PRD changes, so status, merge SHA and evidence survive renames and reordering.

## Alternatives

- **Markdown as state.** Readable, but ambiguous to parse and impossible to validate. Rejected.
- **SQLite.** Transactional and queryable, but opaque to an agent reading files, harder to inspect in a review and more than the data volume needs: a run holds tens of tasks, not thousands of rows. Rejected for now.
- **An external service** such as Redis or a hosted database. Adds an installation step, a network dependency and credentials to a tool that must work offline. Rejected, see [0003](./0003-no-langgraph-redis-vector-memory.md).
- **Agent memory only.** Lost on compaction or provider change. Rejected.

## Consequences

- Any agent, on any provider, can resume a run by reading three small files.
- State changes are deterministic and testable without a model.
- Concurrent writers are not coordinated beyond atomic replacement. Parallel agents must go through the `jotta` command for each update instead of editing the files.
- Revisit if runs grow to a size where whole-file rewrites become slow, or if several processes need to update state at the same time. SQLite would then be the next step.
