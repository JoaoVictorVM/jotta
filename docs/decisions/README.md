# Design decisions

Architecture decision records (ADRs) explain why Jotta is built the way it is. Each record states the context, the decision, the alternatives that were rejected and the consequences that follow.

| ADR | Decision | Status |
|---|---|---|
| [0001](./0001-json-as-source-of-truth.md) | JSON files are the source of truth for run state | Accepted |
| [0002](./0002-lean-as-default-profile.md) | `lean` is the default profile for autonomous work | Accepted |
| [0003](./0003-no-langgraph-redis-vector-memory.md) | No orchestration framework, external store or vector memory | Accepted |
| [0004](./0004-merge-commit-strategy.md) | Pull requests merge with a merge commit | Accepted |

## Writing a new record

Copy the [template](./template.md) to the next free number, such as `0005-short-title.md`. A record is never edited to change its decision: a new record supersedes it, and the old one changes its status to `Superseded by 000N`.
