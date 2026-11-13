# Policy

This folder holds the rules that limit execution.

| File | Contents |
|---|---|
| `permissions.md` | Actions that are allowed, denied or enabled per profile |
| `human-gates.md` | Situations that require a human decision |
| `budget.json` | Budget limits, decision thresholds and checkpoints |
| `providers.json` | Where each provider's usage comes from |
| `routing.json` | Model tier per task and models per provider |

## Budget control

The budget guard combines two independent measures:

- global usage reported by the provider, when available;
- local execution usage, computed from tokens and estimated cost.

The highest known percentage drives the decision. A missing measurement is never presented as a real zero. The source is recorded in `.jotta/runtime/state/usage.json`.

`providers.json` declares the active source. The harness never invents a quota API: when the platform offers a usage tool, the agent queries it and records the percentage with `record`. When it does not, the agent records `unavailable` and only the local execution limits apply, as the policy defines.

### Commands

```powershell
jotta budget status
jotta budget check --checkpoint before-feature --scope feature
jotta budget record --input-tokens 1200 --output-tokens 300 --estimated-cost-usd 0.08
jotta budget record --provider-usage-percent 82 --source provider-api
jotta budget record --provider-usage-unavailable
jotta budget reserve --id spec-f03 --input-tokens 20000 --output-tokens 5000 --estimated-cost-usd 1.00
jotta budget release --id spec-f03
jotta budget authorize --scope feature --until-percent 90 --reason "finish the current feature"
jotta budget clear-authorization
```

### Exit codes

| Code | Meaning |
|---|---|
| 0 | Can continue, including a warning or a valid authorization |
| 2 | Human gate required |
| 3 | Hard stop, cannot be overridden |
| 4 | Required measurement unavailable |

An authorization applies only to the recorded scope and never goes past the hard stop. The orchestrator checks the budget between steps. No sensor can interrupt a model response that is already in progress.

## Model routing

Skills describe how to work. The orchestrator chooses the model before creating the agent that runs the skill.

`routing.json` uses capability tiers to avoid depending on unstable commercial names. By default `spec-writer` uses `efficient`, while implementation and review use stronger tiers.

### Configure an exact model

Use the identifier the platform accepts, not just the marketing name. Illustrative example:

```json
"anthropic": {
  "efficient": "EXACT_ID_OF_THE_CONFIGURED_MODEL",
  "balanced": null,
  "strong": null,
  "review": null
}
```

Then validate and resolve the route:

```powershell
jotta models validate
jotta models resolve --task spec-writer --provider anthropic
```

A `null` value means the harness inherits the platform's model. If the platform does not allow choosing a model per agent, the route is only a declared preference. The orchestrator records the model it actually used and never claims to have applied a route without evidence.

A cheaper model does not lower the skill's requirements, validations or human gates. If the observed quality drops, change the route, not the skill's contract.

### OpenCode and Orca

OpenCode can route to multiple providers, so configure exact provider model IDs in `routing.json` and pass the provider key to `jotta prepare`. The Orca agent id is separate and must match the installed Orca guide. See `.jotta/adapters/opencode/README.md`.
