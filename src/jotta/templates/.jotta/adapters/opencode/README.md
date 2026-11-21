# OpenCode adapter

OpenCode reads the root `AGENTS.md` on its own. `jotta install` and `jotta adapter opencode` generate the rest:

| File | Source |
|---|---|
| `.opencode/opencode.jsonc` | Permission rules from the `deny` list of `.jotta/policy/permissions.md`. Not written when the project keeps its own `.opencode/opencode.json`. |
| `.opencode/agents/<role>.md` | One subagent per role in `.jotta/agents/`. Reviewers cannot edit or run shell commands, and the spec author cannot run shell commands. |
| `.opencode/skills/<skill>/SKILL.md` | One entry per skill in `.jotta/skills/`, which sends the agent to the canonical file. |

OpenCode has no command hooks, so the smoke check after an edit and the quality receipt before stopping are not enforced there: run `jotta quality smoke`, which records the receipt, before you finish. The files under `.jotta/` are the source: edit them and run `jotta adapter opencode` again; never edit the generated files.

## Models

The harness stores capability routes, while OpenCode owns provider credentials and exact model availability.

1. List the exact model identifiers exposed by the installed OpenCode version.
2. Put those identifiers in `.jotta/policy/routing.json` under `providers.openai` or `providers.anthropic`.
3. Resolve a route with `jotta models resolve --task <task> --provider <provider>`.
4. Start the run with `jotta prepare ... --agent <installed-orca-agent-id> --provider <provider>`.

For example, if Orca exposes the OpenCode installation as `omp`, use `--agent omp`. Do not assume this id: use the id reported by the installed Orca guide or agent list. `platform` with null mappings inherits the model already selected by the active tool.

Provider selection and agent selection are independent. An OpenCode agent can use an OpenAI or Anthropic model when that provider is configured in OpenCode. A null route never invents a model name and never claims a switch occurred.
