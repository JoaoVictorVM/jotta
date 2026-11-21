# OpenCode adapter

OpenCode reads `AGENTS.md` by itself, so a project installed with Jotta already gets its instructions. The adapter adds the permission rules, the subagents and the skills.

```bash
jotta adapter opencode            # generate or refresh the OpenCode configuration
jotta adapter opencode --dry-run  # show what would change
```

`jotta install` runs it next to the [Claude Code](./claude-code.md) and [Codex](./codex.md) adapters. The generated files follow the OpenCode V2 configuration: a `permissions` rule list, `shell` and `subagent` action names, and agents in `.opencode/agents/`.

## What is generated

| File | Content |
|---|---|
| `.opencode/opencode.jsonc` | The `$schema` and a `permissions` list with the shell rules of the active [profile](./profiles.md#permissions-per-profile) and rules built from the `deny` list of `.jotta/policy/permissions.md`. |
| `.opencode/agents/<role>.md` | A subagent per role in `.jotta/agents/`, with `description`, `mode: subagent` and the role as its prompt. |
| `.opencode/skills/<skill>/SKILL.md` | The skill's name and description, and an instruction to read the canonical file. |

A file without the Jotta marker is never changed and is reported in `skipped`. When the project keeps its own `.opencode/opencode.json`, the adapter does not write `opencode.jsonc` next to it: merge the rules by hand, or remove your file and run the adapter again. `jotta doctor` warns when a project with `.opencode/` lacks the generated rules.

## The permission rules

OpenCode checks every rule in order, and the last one that matches wins. Its built-in rules allow everything. The adapter first asks before any shell command and adds the allow, ask and deny rules of the active profile, then adds these fixed rules, which no profile relaxes:

| Policy rule | OpenCode rules |
|---|---|
| `read-secrets`, `commit-secrets` | `read` and `edit` denied for the credential files the hooks know, such as `.env`, `*.pem` and `id_rsa*`, and for `.ssh/`, `.aws/` and `.gnupg/`. Files ending in `.example`, `.sample`, `.template`, `.dist` or `.pub` stay allowed outside those folders. |
| `force-push` | `git push` with `-f`, `--force`, `--mirror`, `--delete`, or a `+` or `:` refspec. |
| `hard-reset` | `git reset --hard`. |
| `bypass-branch-protection` | `--no-verify` on `git push` and `git commit`, and `gh pr merge --admin`. |
| `widen-scope` | `jotta scope allow`. |
| `delete-outside-project` | `external_directory` asks before the agent touches anything outside the project. |

The reviewers cannot edit or run shell commands, and the spec author cannot run shell commands. Their rules come after the project rules, so they never relax a denied secret.

## Parity with Claude Code

| Capability | Claude Code | OpenCode |
|---|---|---|
| Block forbidden shell commands | `PreToolUse` hook, parsed by Jotta | `shell` rules, matched as patterns on each subcommand |
| Block secret reads by file tools | `PreToolUse` hook | `read` and `edit` rules |
| Block secret reads through the shell | The hook checks every argument | Not covered: a shell command that reads a secret is allowed |
| Task edit scope | `PreToolUse` hook | Not enforced |
| Smoke after an edit | `PostToolUse` hook | Not enforced; run `jotta quality smoke` |
| Receipt before stopping | `Stop` hook | Not enforced; `jotta quality` records it when the agent runs it |
| Read-only reviewers | Tool list limited to `Read`, `Grep`, `Glob` | `edit` and `shell` denied for the agent |
| Skills | `.claude/skills/` | `.opencode/skills/` |
| `deploy-production` | Human gate in the workflow | Human gate in the workflow; no rule can recognize a deploy command |

Patterns are simpler than the hook guard: a combined short flag such as `git push -uf` or a command built at runtime is not recognized. OpenCode plugins could close these gaps, but their API is changing between versions, so the adapter does not generate one yet.
