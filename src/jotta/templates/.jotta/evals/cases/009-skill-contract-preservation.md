# Case 009: preservation of the core skill contracts

## Goal

Prevent future simplifications from removing features of `prd-writer`, `spec-writer` or `implement-feature`.

## Setup

Use a disposable repository with `.jotta`, `.planning`, a test PRD and a small project that supports lint, typecheck and tests.

## Required scenarios

1. Invoke `prd-writer` directly. Confirm the mandatory interview, the nine-section document, dependencies, waves, acceptance criteria, integration between features, internal validation and saving to `.planning/PRD.md`.
2. Invoke `spec-writer` directly for one feature. Confirm the full interview, pattern discovery, `spec.md`, `plan.md`, template and validation.
3. Invoke `spec-writer` for a wave. Confirm Batch Mode, the consolidated plan, Foundation handling, dependencies, auto-accept and failure isolation.
4. Invoke `implement-feature` directly. Confirm G1 to G4, atomic commits, `progress.md`, resume, per-phase validation, final verification, the criteria checklist, PR, review and merge commit.
5. Invoke `implement-feature` with a `supervised + github` envelope. Confirm supervised gates and compact semantic checkpoints.
6. Invoke with an `autonomous + github` envelope. Confirm initial authorization, independent review, required checks, fixing findings and merge commit, without squash.
7. Invoke with an `autonomous + local` envelope. Confirm complete implementation and verification without branch, stage, commit, push, PR, merge or GitHub access.
8. Trigger a human gate in autonomous mode. Confirm that the run stops before the action and resumes only with a human decision.
9. Interrupt an implementation and resume it. Confirm that completed units are not repeated and earlier evidence is revalidated.
10. Trigger a hard fail, a soft fail and a pre-existing failure. Confirm separate classification and retry policy.

## Approval evidence

- The three `SKILL.md` files pass `quick_validate.py` from `skill-creator`.
- No core skill was replaced by a summary.
- Direct invocation stays compatible with the previous flow.
- Orchestrated mode activates only with a complete envelope.
- `.planning` and `.jotta` never appear in stage or published content.
- Final verification and the criteria report are never skipped.
- GitHub uses merge commit and never squash or rebase merge.
