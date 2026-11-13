# Architecture

Jotta has two parts: a Python package with the `jotta` command, and the harness content that `jotta install` copies into a project.

## Package and installed harness

| Part | Location | Role |
|---|---|---|
| Package | `src/jotta/` | Deterministic work: parsing the PRD, state, budget, model routing, quality gates, isolation and installation. |
| Templates | `src/jotta/templates/` | What a project receives: `AGENTS.md`, `CLAUDE.md`, `.jotta/` and `.planning/`. |
| Harness | `.jotta/` in the project | Workflows, profiles, skills, agents, guides, sensors, policy, prompts and memory. |
| Planning | `.planning/` in the project | PRD, feature specs and plans, change briefs and commit plans. |
| Runtime | `.jotta/runtime/` in the project | Execution state, context packets, quality receipts and full logs. Created on demand and ignored by Git. |

## Principles

- `AGENTS.md` is an index. Agents read the smallest applicable set of documents.
- Three workflows cover product, change and quality. See [workflows](./workflows.md).
- Profiles control intensity without duplicating workflows. See [profiles](./profiles.md).
- Skills use progressive disclosure. The manual and strict contracts remain complete, while lean loads compact references.
- The `jotta` command performs deterministic work. Models handle semantic decisions.
- Guides act before the agent and sensors check after it. See [guides and sensors](./guides-and-sensors.md).
- JSON is state and Markdown is a human projection. See [state machine](./state-machine.md).
- Full logs stay outside model context unless needed. Models receive compact receipts.
- Budget gates and model routing run between steps. See [budget and routing](./budget-and-routing.md).
- Autonomous GitHub writers use Orca-managed worktrees and visible sessions.
- A lean delivery reuses its worktree through feature checkpoints and opens one final pull request.
- GitHub uses merge commits. Lean prefers one semantic commit per feature and splits only when rollback value is clear.
- Planning and harness artifacts stay local to the project unless it chooses to version them.

## Non-goals

No database, LangChain, LangGraph, knowledge graph, multi-model council, deployment automation or automatic memory inference. Each mechanism must be justified by a failure it prevents, as described in [model assumptions](../model-assumptions.md).
