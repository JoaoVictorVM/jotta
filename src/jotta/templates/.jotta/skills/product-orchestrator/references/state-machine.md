# State machine

The runtime keeps only restartable evidence in `.harness/state/current-run.json`.

```text
idle -> prepared -> implementing -> validating -> completed-local
idle -> prepared -> worktree-ready -> implementing -> validating -> pr-open -> merged -> cleaned
any active state -> blocked | failed | cancelled
```

Feature status in `.harness/state/tasks.json` is independent:

```text
pending -> ready -> specifying -> implementing -> validating -> completed
any active state -> blocked | failed | cancelled
```

In `lean`, a completed feature advances the next dependency without opening a PR or invoking a semantic reviewer. The product branch receives one final PR after final QA. In `strict`, feature-level review is allowed. In `manual-classic`, the preserved skill contracts define G1 to G4.

Every transition needs compact evidence. GitHub completion requires a merge SHA. Local completion requires a quality receipt. Cleanup requires merged status, merge SHA, clean worktree confirmation and a recorded Orca worktree. Write state atomically and regenerate `progress.md`.

When the PRD hash changes, reconcile by stable ID. Add new IDs, preserve unchanged statuses and request a human decision if a completed feature changed.
