# Case 010: budget guard

## Goal

Validate warning, human gate, limited authorization, reservations and hard stop.

## Scenarios

1. With usage below 70%, `check` returns code 0 and `continue`.
2. At 70%, it returns code 0 and `warning`.
3. At 85%, it returns code 2 and `human-gate`.
4. Authorize only `feature` up to 90%. Confirm that the feature continues and the wave does not inherit the authorization.
5. At 95%, confirm code 3 even with an earlier authorization.
6. Reserve parallel agents and confirm that the reservation counts toward the percentage before dispatch.
7. Release the reservation and confirm it is removed.
8. Mark provider usage as unavailable and confirm the fallback to the local budget.

## Approval

The flow never presents a local estimate as the provider's real percentage and never goes past the hard stop.
