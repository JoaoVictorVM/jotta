---
name: implement-feature
description: Implement a planned feature under manual-classic, lean or strict execution. Keeps the original supervised and exhaustive contract available while giving autonomous product runs a compact worktree-aware path.
---

# Implement Feature

Resolve the execution profile from the complete `HARNESS_RUN` envelope.

- Direct invocation, incomplete envelope, `manual-classic`, or `strict`: read [references/manual-classic-and-strict.md](references/manual-classic-and-strict.md) completely. It preserves the original G1 to G4 flow, exhaustive validation, GitHub behavior, reporting, resume behavior and edge cases.
- `lean`: read [references/lean.md](references/lean.md). Do not also load the classic contract.

Shared invariants for every profile:

- Planning and harness files remain local through `.git/info/exclude`.
- Never publish planning IDs, AI attribution or forbidden text.
- Stage explicit paths only.
- A writer works only in its assigned checkout or Orca worktree.
- Human gates override autonomy.
- Never claim success without the evidence required by the active profile.
