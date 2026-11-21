# Profiles

A profile sets how much rigor a run applies. All profiles use the same [workflows](./workflows.md); they change how specs are reviewed, how much validation runs and when code is reviewed.

## Comparison

The values come from `.jotta/profiles/*.yaml`.

| Setting | `manual-classic` | `lean` | `strict` |
|---|---|---|---|
| Spec review | Manual, by the user | Only for high-risk work | Always |
| Validation | Per feature | `smoke` per feature | Per phase and per feature |
| Code review | Manual | Once, at the end | Per feature |
| Commits | Atomic | Compact and semantic | Compact and semantic |
| Worktree | When requested | Always for autonomous GitHub | Always for autonomous GitHub |
| Final QA | Manual | For the product | For the product |

- **manual-classic** keeps the original, detailed contracts: interviews, the human gates G1 to G4, plans and detailed validation. It is the compatibility path for the earlier workflow.
- **lean** is the autonomous default. It loads compact references, runs `smoke` checks per feature, skips per-feature reviewers for low-risk work and concentrates semantic review at the end of the scope.
- **strict** reuses the complete contracts with automation and reviews every spec and every feature.

## Permissions per profile

`.jotta/policy/profile-permissions.json` turns the profile into shell permissions, which the [adapters](./claude-code.md) write into each agent's own settings. Every profile allows read-only Git commands, `ls`, `pwd`, the read-only `jotta` commands and the commands of the quality profiles.

| Command | `manual-classic` | `lean` | `strict` |
|---|---|---|---|
| `git add` | Ask | Allow | Allow |
| `git commit` | Ask | Allow | Ask |
| `git push`, `gh pr create` | Ask | Ask | Ask |
| `gh pr merge` | Deny | Ask | Ask |
| Other `jotta` commands | Ask for `prepare` and `checkpoint` | Allow | Allow |
| Dependency installs | Default | Default | Ask |

Anything else follows the agent's default, which asks in Claude Code and OpenCode and runs inside the sandbox in Codex. A denial in `permissions.md`, such as a force push, is enforced by the hooks and never relaxed by a profile.

The adapters read the profile from `defaults.execution_profile` in `.jotta/config.yaml`, or from `--profile`:

```bash
jotta adapter claude --profile strict
```

After changing the configured profile, run the adapters again; `jotta doctor` warns while a generated configuration is out of date. Each agent receives the rules in its own format:

| Agent | Where | Notes |
|---|---|---|
| Claude Code | `permissions.allow`, `ask` and `deny` in `.claude/settings.json`, as `Bash(<pattern>)` | `.claude/jotta-permissions.json` records the rules Jotta added, so a profile change replaces them and keeps yours. |
| Codex | `.codex/rules/jotta.rules`, as `prefix_rule` | Only `ask` (`prompt`) and `deny` (`forbidden`): an `allow` rule would run the command outside the sandbox. |
| OpenCode | The `permissions` list of `.opencode/opencode.jsonc` | A broad `ask` comes first, then the allow, ask and deny rules, and the fixed denials of the policy last. |

## Selection

1. A profile the user names explicitly always wins.
2. Invoking a skill directly defaults to `manual-classic`.
3. Autonomous product work defaults to `lean`.
4. `strict` is used when requested or when risk requires it.

## Risk elevation

`jotta prepare` classifies the task text, the matching PRD excerpt and the feature spec. When they mention a high-risk topic, such as authentication, authorization, payments, billing, secrets, security, schema migrations, personal data, permissions, production, infrastructure, public APIs or breaking changes, a `lean` request runs as `strict`. The context packet records both profiles and the matched terms under `risk`, and the implementer is routed to the high-risk model route.

## Quality per profile

`.jotta/config.yaml` maps profiles to the quality gates in `.jotta/sensors/computational/gates.json`.

| Moment | Lean | Final |
|---|---|---|
| After each feature | `smoke` | |
| After each wave | `feature` | |
| Before delivery | | `full` and final QA |

An empty quality profile returns `skipped`, never a false pass.
