# Case 011: model routing

## Goal

Validate per-task selection without reducing the skill contracts.

## Scenarios

1. Run `jotta models validate`.
2. Resolve `spec-writer` and confirm tier `efficient`.
3. Resolve `implement-feature` and confirm tier `strong`.
4. Resolve `pr-reviewer` and confirm tier `review`.
5. With a null model and the `inherit` policy, confirm the inherited model without a false claim of switching.
6. Configure a valid provider ID and confirm a `resolved` result.
7. Simulate a platform without per-agent selection and confirm that the inherited effective model is recorded.
8. Confirm that switching models does not remove interviews, validation, review or human gates.

## Approval

Every agent creation records task, tier, preference, effective model and decision source.
