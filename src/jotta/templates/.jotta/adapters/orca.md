# Orca adapter

Use Orca for worktree creation, visible agent sessions, terminal control and cleanup. Do not use raw `git worktree` for Orca-managed lanes.

## Resolve and load

Resolve the executable once: `ORCA_CLI_COMMAND`, then `orca-dev` in a dev checkout, `orca-ide` on Linux outside Orca, otherwise `orca`. Run `ORCA skills get orca-cli --json` before operations. If it is unavailable, report the exact error and follow the configured fallback. Do not guess flags.

## Create and launch

For an independent feature based on the repository default base:

```text
ORCA worktree create --name <slug> --no-parent --agent <agent> --model <model> --effort <effort> --surface terminal --activate --prompt "<compact task brief>" --json
```

Omit unsupported optional flags only when the version-matched guide says to. Save the complete `result.id` and `result.launch.outcome.handle`. `--agent` already launches the model, so never start it again.

For a worker in an existing Orca worktree:

```text
ORCA agent launch --agent <agent> --worktree id:<repoId>::<path> --surface terminal --prompt "<brief>" --json
```

## Observe

Read before sending input. Use the exact returned handle. Do not resend an accepted prompt merely because output is silent. Update the worktree comment at implementation, validation, review and blocker checkpoints.

## Cleanup

Only after merge confirmation and a clean, recoverable lane:

```text
ORCA terminal close --worktree id:<repoId>::<path> --all --json
ORCA worktree rm --worktree id:<repoId>::<path> --json
```

Do not add `--force` unless the user explicitly authorizes that exact destructive cleanup and all unique work is preserved. If cleanup is unverifiable, keep the lane and report it.
