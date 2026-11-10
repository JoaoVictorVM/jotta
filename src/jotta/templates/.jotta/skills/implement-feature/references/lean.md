# Lean implementation contract

Use only with a complete `HARNESS_RUN` whose profile is `lean`.

## Context and isolation

Read the prepared context packet, `spec.md`, `plan.md`, acceptance criteria and current task state. Open code lazily. For autonomous GitHub, require the Orca worktree and worker handle recorded by `prepare`; do not implement in the main checkout.

## Implementation

1. Confirm dependencies and allowed paths.
2. Implement the smallest complete behavior described by the spec.
3. Add or update targeted tests when the repository has a test pattern.
4. Run the configured `smoke` quality profile once after the coherent feature change. Fix failures caused by the change within the retry limit.
5. Produce 1 to 3 compact semantic commits for GitHub destinations. Local destinations create no commits or Git mutations.
6. For GitHub, push, open the PR, wait for required CI and merge with a merge commit when preauthorized and no human gate is pending.
7. Record compact evidence and call `harness.py finish`. Cleanup is allowed only after merge is confirmed and the worktree is clean.

## Review and validation

Do not create a separate spec or PR reviewer for an ordinary low-risk feature. High-risk tasks marked by `prepare` use the strict review path. Product and wave review occur through `final-qa` after their scope completes.

- Per feature: configured smoke commands and targeted runtime exercise when cheap and available.
- Per wave: integration commands selected by the product workflow.
- End of product: full quality profile and final QA.
- Store full command output in `.harness/runtime/logs/`; return only the compact receipt.
- Screenshots and visual QA are opt-in for UI acceptance or explicit request.

## Git and result

Never force push, rewrite published history, bypass protection or stage local paths. A failed CI, unresolved conflict or missing authority blocks merge. Return status, changed files, compact validation receipts, acceptance evidence, deviations and blockers. Do not repeat the full spec or test logs.
