---
name: change-intake
description: Classify an unspecced request as bug, small change, refactor, feature extension or product revision and create the minimum local planning artifact. Do not implement the change.
---

# Change Intake

Read the current PRD, relevant code and `.harness/workflows/change-intake.md`.

1. Determine current and expected behavior.
2. Classify the request.
3. Create the minimum artifact under `.planning/changes/` or update the PRD for a feature.
4. Add a task to state with type, source, affected features and criteria.
5. Return scope, profile and destination to the orchestrator.

Use a human gate for product ambiguity, completed-feature contract changes, authentication, payments, personal data or major direction changes.

