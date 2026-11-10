---
name: spec-writer
description: Produce a feature spec and implementation plan from the local PRD and current codebase. Routes manual and strict runs to the preserved full contract and lean product runs to a compact non-interactive contract.
---

# Spec Writer

Resolve the execution profile from the complete `HARNESS_RUN` envelope.

- Direct invocation, `manual-classic`, or `strict`: read [references/manual-classic.md](references/manual-classic.md) completely and follow it. This preserves the original interview, Batch Mode, discovery, validation, edge cases and templates.
- `lean`: read [references/lean.md](references/lean.md). Do not also load the classic contract.
- Missing or incomplete envelope: use `manual-classic`.

All profiles keep planning under `.planning/features/<feature-id>-<slug>/`, never publish planning artifacts and generate both `spec.md` and `plan.md`.
