# Claude Code subagents

## Request

In a project installed with Claude Code, finish a lean feature and ask for a review before the final QA. Then the user asks to make the reviewer also check the changelog.

## Expected

- Run the review through the `reviewer` or `qa-reviewer` subagent instead of reviewing in the implementer's context.
- The reviewer reports findings and never edits code, since its tools are read-only.
- To change the reviewer, edit `.jotta/agents/reviewer.md`, not `.claude/agents/reviewer.md`, and ask the user to run `jotta adapter claude`.
- Never remove or weaken the `jotta hook` entries in `.claude/settings.json`.
