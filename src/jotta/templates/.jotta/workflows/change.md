# Workflow: change

Use for a bug, small adjustment, refactor, feature extension or product revision.

1. Classify the request and create only the minimum planning artifact under `.planning/changes/<slug>/`.
2. A clear bug needs reproduction, expected behavior and regression evidence. A small change needs objective, exclusions and acceptance criteria. A feature updates the PRD and receives a feature spec. A major product direction change stops at a human gate.
3. Run `harness.py prepare <task>` with the selected interaction, destination and profile.
4. Implement through `implement-feature` when a feature plan exists, otherwise use the compact change brief.
5. Apply the same risk, isolation, quality and finish rules as the product workflow.
6. Archive completed change artifacts under `.planning/archive/changes/` when useful. Never publish them.
