---
name: prd-writer
description: Create or revise the local product PRD through the established interview, dependency, wave, validation and nine-section contract. Use for product definition, not ordinary feature implementation.
---

# PRD Writer

The established PRD behavior is preserved in [references/full-contract.md](references/full-contract.md). Read it completely before creating or revising a PRD. It remains authoritative for the interview, nine-section document, feature dependencies, execution waves, validation, examples and edge cases.

When `.harness` and `.planning` exist:

- Default the output to `.planning/PRD.md`.
- Keep the PRD local. Never stage, commit, push or cite it in published content.
- Preserve existing feature IDs during revision. New features receive the next unused IDs.
- Stop at the configured human gate before changing the contract of a completed feature.
- After saving, run `python .harness/scripts/harness.py sync-tasks`.

Do not load this skill during product execution when a valid PRD already exists.
