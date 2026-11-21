# Codex adapter

The root `AGENTS.md` is the entry point. `jotta install` and `jotta adapter codex` generate the native configuration:

| File | Source |
|---|---|
| `.codex/hooks.json` | The `PreToolUse`, `PostToolUse` and `Stop` hooks, which call `jotta hook <event> --agent codex`. Existing hooks are kept. |
| `.codex/config.toml` | `approval_policy = "on-request"` and the `workspace-write` sandbox without network. Written only when absent or generated. |
| `.codex/agents/<role>.toml` | One custom agent per role in `.jotta/agents/`. Reviewers are told to stay read-only. |
| `.agents/skills/<skill>/SKILL.md` | One entry per skill in `.jotta/skills/`, which sends the agent to the canonical file. |

Codex reads `.codex/` only in a trusted project, and runs a project hook only after you review it with `/hooks`. The files under `.jotta/` are the source: edit them and run `jotta adapter codex` again; never edit the generated files. A file Jotta did not generate is never overwritten.
