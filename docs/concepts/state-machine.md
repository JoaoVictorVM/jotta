# State machine

The runtime keeps only restartable evidence. JSON files are the source of truth; Markdown files are generated for people.

## Files

All files live under `.jotta/runtime/` in the project and are ignored by Git. None of them ships with the templates: when a file is missing, the runtime starts from an empty default and creates it on the first write.

| File | Contents | Written by |
|---|---|---|
| `state/current-run.json` | The active run: scope, profile, stage, current task, worktree, workers, blocker, pull request and merge SHA | `prepare`, `checkpoint`, `finish` |
| `state/tasks.json` | One entry per PRD feature with dependencies, wave, status and evidence | `sync-tasks`, `checkpoint`, `finish` |
| `state/usage.json` | Token and cost usage per stage, provider usage, reservations and budget authorization | `budget`, `checkpoint`, `finish` |
| `state/progress.md` | Tasks grouped by status, for people | `progress` |
| `context/<task>-<role>.json` | The compact context packet for one task and role | `prepare` |
| `receipts/` and `logs/` | Quality receipts and full command output | `quality` |

## Run states

```text
idle -> preparing -> running -> completed-local
idle -> preparing -> running -> merged
any active state -> blocked | failed | cancelled
```

- `jotta prepare` moves the run to `preparing`, or to `running` once an Orca worktree is launched or reused.
- `jotta checkpoint` keeps the run `running`, or sets `blocked` or `failed` with a blocker. A budget gate after the feature can also block it.
- `jotta finish` records the final status. `merged` requires `--merge-sha`, and `--cleanup` additionally requires `--worktree-clean` and a recorded worktree.

## Task states

```text
pending -> ready -> specifying -> implementing -> validating -> completed
any active state -> blocked | failed | cancelled
```

The commands set `ready` and `pending` when synchronizing and the final statuses through `checkpoint` and `finish`; the intermediate statuses are recorded by the orchestrator when it tracks them. `jotta sync-tasks` marks a task `ready` when all its dependencies are completed, merged or completed locally, and `pending` otherwise. `jotta prepare` refuses a task whose dependencies are not done.

## Evidence

Every transition needs compact evidence: a quality receipt for local completion, a merge SHA for GitHub completion, and a merge SHA, clean worktree confirmation and recorded Orca worktree for cleanup. Writes are atomic: each file is written to a temporary file and then replaced.

## PRD changes

`tasks.json` stores the PRD hash. When the PRD changes, `jotta sync-tasks` reconciles by stable feature ID: new IDs are added and existing statuses are preserved. If a completed feature changed, the agent asks for a human decision.

## Context packets

A packet contains the task, the requested and effective profiles, the risk classification, the budget evaluation, the model route, the relevant PRD excerpt, the paths of an existing spec and plan, and the control root. It includes the control root because `.jotta/` and `.planning/` are local and are not copied into a Git worktree: the worker writes code in the worktree while the orchestrator keeps planning and state in the control root.
