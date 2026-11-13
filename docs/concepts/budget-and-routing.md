# Budget and routing

Both run between steps. Neither can interrupt a model call that is already in progress.

## Budget

The policy lives in `.jotta/policy/budget.json` and the usage in `.jotta/runtime/state/usage.json`.

### Measurement

The budget guard combines two independent measures and uses the higher one:

- **Provider usage**: the percentage of the provider quota, recorded with `jotta budget record --provider-usage-percent` when the platform exposes it. `.jotta/policy/providers.json` declares where that number comes from. The harness never invents a quota API.
- **Execution usage**: input tokens, output tokens and estimated cost against the run limits in the policy, including active reservations.

A missing measurement is never reported as zero. The source of the effective percentage is recorded.

### Decisions

| Status | Condition | Exit code |
|---|---|---|
| `continue` | Below the warning threshold (70% by default) | 0 |
| `warning` | At or above the warning threshold | 0 |
| `human-gate` | At or above the human gate (85%) without an applicable authorization | 2 |
| `authorized` | Above the human gate with an authorization for this scope | 0 |
| `hard-stop` | At or above the hard stop (95%); cannot be overridden | 3 |
| `measurement-unavailable` | Provider usage is missing and the policy requires it | 4 |
| `disabled` | The policy is disabled | 0 |

`jotta prepare` checks the budget before each task, using the run scope for a product, the wave scope for the next wave and the feature scope otherwise. `jotta checkpoint` checks it again after each feature.

### Authorizations and reservations

- `jotta budget authorize --scope <feature|wave|run> --until-percent <n> --reason <text>` lets the run continue past the human gate. The limit must be at least the human gate and below the hard stop, and a feature authorization does not apply to a wave.
- `jotta budget reserve` counts the expected usage of parallel agents before they are dispatched; `jotta budget release` removes the reservation.

## Model routing

`.jotta/policy/routing.json` uses capability tiers instead of commercial model names.

| Tier | Purpose | Fallback |
|---|---|---|
| `efficient` | Documents and low-risk classification | `balanced` |
| `balanced` | Orchestration and ordinary implementation | `strong` |
| `strong` | Complex implementation and high-impact decisions | none |
| `review` | Independent final or high-risk review | `strong` |

Each task has a tier and an optional preferred model, and each provider maps tiers to exact model IDs.

### Resolution

1. A preferred model for the task wins.
2. Otherwise the provider's model for the task's tier is used, following the fallback chain when a tier has no model.
3. If no model is found, `unavailable_behavior` decides: `inherit` uses the platform's model (exit code 0), while `gate` and `fail` report the route as unavailable (exit code 3).

`jotta prepare` resolves the route from the role: the implementer uses `implement-feature`, or `implement-feature-high-risk` when the effective profile is `strict`; the spec author uses `spec-writer`; the QA reviewer uses `final-qa`; and the orchestrator uses `product-orchestrator`. `--model` overrides the result.

When the platform cannot select a model per agent, the route is only a declared preference. The orchestrator records the model it actually used and never claims a route it cannot prove. A cheaper model never lowers the skill's requirements, validations or human gates.
