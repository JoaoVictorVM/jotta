---
name: commit-manager
description: Plan logical commits from an uncommitted or non-Git project, or apply a previously generated commit plan. Planning never mutates Git; apply verifies fingerprints before staging, committing or optionally pushing.
---

# Commit Manager

## Plan mode

Read [references/plan-schema.md](references/plan-schema.md). Inventory eligible files, exclude secrets and generated content, distinguish uncommitted work from commits ahead of upstream, and write matching Markdown and JSON plans under `.planning/commit-plans/`. Do not mutate Git.

## Apply mode

Require a plan path. Recompute fingerprints and stop on drift. Stage explicit paths, run commit gates and create commits in order. Push only when explicitly requested. Creating a remote repository requires explicit name and visibility.

In the MVP, one file appears in only one planned commit. When a file contains inseparable logical changes, keep it in the broader coherent commit rather than using hunk staging.

