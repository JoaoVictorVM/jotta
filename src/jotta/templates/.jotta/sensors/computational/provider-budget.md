# Sensor: provider budget

## Command

```powershell
jotta budget check --checkpoint <checkpoint> --scope <feature|wave|run>
```

## Evidence

Record the status, the effective percentage and its source, the local percentage, the provider percentage, reservations and the applicable authorization.

## Decision

- Code 0: continue, and record a warning when there is one.
- Code 2: trigger `provider-budget-threshold` and wait for a human decision.
- Code 3: stop at the hard stop.
- Code 4: apply the policy for unavailable measurement.

The sensor runs between steps and does not interrupt a model call in progress.
