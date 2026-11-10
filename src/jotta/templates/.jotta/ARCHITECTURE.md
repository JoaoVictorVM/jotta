# Harness architecture v0.5

- `.harness` contains mechanism, configuration, local state and operational knowledge.
- `.planning` contains local PRD, specs, plans and change packages.
- `AGENTS.md` is an index only.
- Three workflows cover product, change and quality.
- Profiles control intensity without duplicating workflows.
- Skills use progressive disclosure. Manual and strict contracts remain complete; lean loads compact references.
- Scripts perform deterministic parsing, state, budget and quality work. Models handle semantic decisions.
- Autonomous GitHub writers use Orca-managed worktrees and visible sessions.
- A lean delivery reuses its worktree through feature checkpoints and opens one final PR.
- Full logs stay outside model context unless needed.
- JSON is state; Markdown is a human projection.
- GitHub uses merge commits. Lean prefers one semantic commit per feature and splits only when rollback value is clear.
- Planning and harness artifacts remain local in the control root.

## Non-goals for v0.5

No database, LangChain, LangGraph, knowledge graph, multi-model council, deployment automation, plugin marketplace or automatic memory inference.
