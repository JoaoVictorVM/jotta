# Claude Code adapter

`CLAUDE.md` imports `AGENTS.md`. `jotta install` and `jotta adapter claude` generate the native configuration under `.claude/`:

| File | Source |
|---|---|
| `.claude/settings.json` | The `PreToolUse`, `PostToolUse` and `Stop` hooks, which call `jotta hook`. Existing settings and hooks are kept. |
| `.claude/agents/<role>.md` | One subagent per role in `.jotta/agents/`. `reviewer` and `qa-reviewer` get read-only tools. |
| `.claude/skills/<skill>/SKILL.md` | One entry per skill in `.jotta/skills/`, which sends the agent to the canonical file. |

The files under `.jotta/` are the source. Edit them and run `jotta adapter claude` again; never edit the generated files, which are replaced. A file under `.claude/` that Jotta did not generate is never overwritten. Tool-specific configuration stays local and never changes the harness policies.
