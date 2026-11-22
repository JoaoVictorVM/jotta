# Budget and routing

Both run between steps. Neither can interrupt a model call that is already in progress.

## Budget

The policy lives in `.jotta/policy/budget.json` and the usage in `.jotta/runtime/state/usage.json`.

### Measurement

The budget guard combines two independent measures and uses the higher one:

- **Provider usage**: the percentage of the provider quota, recorded with `jotta budget record --provider-usage-percent` when the platform exposes it. `.jotta/policy/providers.json` declares where that number comes from. The harness never invents a quota API.
- **Execution usage**: input tokens, output tokens and estimated cost against the run limits in the policy, including active reservations.

A missing measurement is never reported as zero. The source of the effective percentage is recorded.

### Measured usage

`jotta usage` reads the local session transcripts of the agents and reports the tokens they really used:

```bash
jotta usage                              # every Claude Code and Codex session of the project
jotta usage --agent codex                # one agent
jotta usage --since 2026-11-20T09:00:00Z # usage at or after a time
jotta usage --session <id>=F03           # assign a whole session to a task
jotta usage --transcript path/to.jsonl   # read given files instead of searching
```

| Agent | Transcripts | One record per |
|---|---|---|
| Claude Code | `~/.claude/projects/<project>/*.jsonl` and `<session>/subagents/*.jsonl`, or under `CLAUDE_CONFIG_DIR` | API response (`message.id`); the copies of a response with several content blocks count once |
| Codex | `~/.codex/sessions/<yyyy>/<mm>/<dd>/*.jsonl` whose session ran in the project, or under `CODEX_HOME` | Response (`token_usage_record`), or `token_count` event in older files, skipping repeated totals |

Each record has four separate counts: uncached input, output, cache read and cache creation. Codex counts cached tokens inside its input, so they are subtracted. The report has totals per model, per agent and per task.

The cost comes from `.jotta/policy/pricing.json`, in US dollars per million tokens, keyed by exact model id or by a pattern such as `claude-opus-*`. Jotta ships no prices, since they change: copy them from the provider's price page. A missing cache price uses the input price; a model without prices is listed in `unpriced_models`, and its messages in `unpriced_messages`, never priced at zero.

A message belongs to the task whose period contains it: `jotta prepare` opens a period and `jotta checkpoint` and `jotta finish` close it, in `.jotta/runtime/state/task-periods.json`. `--session` overrides the period for a whole session. Usage outside every period is reported as `unassigned`. The command only reads; the budget guard still uses the recorded usage.

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
