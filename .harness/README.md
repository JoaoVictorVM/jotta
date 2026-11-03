# jotta v0.5

A local-first, spec-driven harness with progressive context, lean autonomous execution, preserved manual workflows and Orca-managed GitHub worktrees.

## Start

1. Copy this package into the project root.
2. Run `python .harness/scripts/bootstrap.py` to create local folders and Git exclusions.
3. Write or revise `.planning/PRD.md` with `prd-writer`.
4. Configure project commands in `.harness/sensors/computational/gates.json`.
5. Run `python .harness/scripts/harness.py doctor`.
6. Copy a prompt from `.harness/prompts/` or ask in natural language.

## Profiles

- `manual-classic`: preserved interviews, G1 to G4 and the original detailed skills.
- `lean`: autonomous default, compact context, smoke validation per feature and one final semantic review.
- `strict`: exhaustive validation and review per feature.

High-risk lean work is elevated to strict by `prepare` and reported before implementation.

## Main requests

```text
Implement the complete product using lean with GitHub.
Implement F03 using manual-classic.
Classify and implement this bug locally.
Run final QA for the product.
Resume the recorded run.
Show harness status.
```

## Internal commands

The agent normally calls these:

```text
python .harness/scripts/harness.py doctor
python .harness/scripts/harness.py sync-tasks
python .harness/scripts/harness.py prepare F03 --profile lean --interaction autonomous --destination github --scope product
python .harness/scripts/run_quality.py smoke
python .harness/scripts/harness.py checkpoint --task F03 --status completed --evidence <receipt>
python .harness/scripts/harness.py finish --status merged --merge-sha <sha> --cleanup --worktree-clean
```

Autonomous GitHub `prepare` launches the required Orca worktree and visible terminal automatically. Use `--defer-worktree` only for inspection or an external launcher. If Orca is unavailable, the run blocks instead of writing in the main checkout.

## Lean lifecycle

```text
prepare first feature and create one delivery worktree
-> generate missing spec
-> implement one feature
-> compact smoke receipt
-> compact semantic commit
-> checkpoint and prepare next feature in the same worktree
-> full quality and final QA for the scope
-> one cumulative PR, green CI and merge commit
-> verified cleanup
```

Full logs live under `.harness/runtime/logs/` and are not inserted into model context by default. Screenshots are created only for UI acceptance or explicit request.

## Configure quality

Example:

```json
{
  "profiles": {
    "smoke": ["npm run typecheck", "npm run test -- --runInBand"],
    "feature": ["npm test"],
    "full": ["npm run lint", "npm run typecheck", "npm test"]
  }
}
```

Use commands appropriate to the project. An empty profile returns `skipped`, never a false pass.

## Budget gate

The runtime checks `.harness/budgets/policy.json` before and after each feature. Provider usage can be recorded when the platform exposes it. At the human-gate threshold, execution stops until an explicit scoped authorization is recorded. The hard stop cannot be overridden by the harness.

## Recovery

Blocked, dirty, unmerged or unverifiable worktrees are preserved. Inspect `current-run.json`, the Orca workspace and compact receipts before resuming. Cleanup never uses force by default.
