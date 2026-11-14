# 0002: Make lean the default profile for autonomous work

- Status: Accepted
- Date: 2026-11-14

## Context

The original workflow, now the `manual-classic` profile, applied the full contract to every feature: interviews, the human gates G1 to G4, detailed plans, validation per phase and a review per feature. That rigor is worth its cost on risky work, but on a product with many low-risk features it multiplies tokens, wall time and human interruptions, and the per-feature reviewer mostly confirms what the tests already showed.

The static skill estimates make the gap visible: the strict contracts load more than ten times the context of the lean references.

## Decision

`lean` is the default profile for autonomous product work.

- Features load compact references instead of the full contracts.
- Each feature runs the `smoke` quality profile and records a checkpoint. Each wave runs the `feature` profile.
- Semantic review is concentrated at the end: a final QA pass and one pull request for the delivery.
- Risk elevation is automatic. `jotta prepare` classifies the task, the PRD excerpt and the spec, and runs high-risk work (authentication, payments, migrations, personal data, public APIs and similar) as `strict`, on the high-risk model route.
- An explicit profile always wins. Invoking a skill directly defaults to `manual-classic`, which keeps the full original contract.

## Alternatives

- **`strict` by default.** Safest, but too expensive for routine features and slow enough to discourage use. Rejected.
- **`manual-classic` by default.** Requires a human at every gate, which defeats autonomous runs. Kept as the compatibility path, not the default.
- **No profiles, one fixed process.** Forces the same cost on a typo fix and on a payment flow. Rejected.

## Consequences

- Autonomous runs are cheaper and interrupt the user less.
- A defect in a low-risk feature can survive until the final QA instead of being caught at its own review. The `smoke` checks, the final `full` profile and the final QA pass are the compensating controls.
- The quality of the risk classifier matters. A sensitive change described in unusual words runs as `lean`. The keyword list is bilingual and tested, and the user can always request `strict`.
- Revisit if evals show that lean deliveries reach the final QA with more critical findings than strict ones.
