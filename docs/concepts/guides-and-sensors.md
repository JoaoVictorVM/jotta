# Guides and sensors

The harness controls an agent in two directions. Guides act before the agent works, so it does the right thing the first time. Sensors check the result afterwards, so mistakes are caught and fed back. Sensors are either computational (deterministic commands) or inferential (a model reviewing with a rubric).

## Guides

| Guide | Location | Purpose |
|---|---|---|
| Index | `AGENTS.md` | Routes each request to the smallest set of documents |
| Manual | `.jotta/AGENT-MANUAL.md` | Request resolution, runtime cycle, roles and completion rules |
| Workflows | `.jotta/workflows/` | Product, change and quality procedures |
| Skills | `.jotta/skills/` | Contracts for PRD, specs, implementation, commits, change intake and QA |
| Rules | `.jotta/guides/rules/` | Git, commits, security, text, comments and planning artifacts |
| Conventions | `.jotta/guides/conventions/project.md` | The project's stack, structure and recurring decisions |
| Templates | `.jotta/guides/templates/` | Spec, plan, change request, commit plan, review report and pull request |
| Policy | `.jotta/policy/` | Permissions, human gates, budget and model routing |
| Memory | `.jotta/memory/learnings.md` | Durable, confirmed learnings |

## Computational sensors

| Command | Checks |
|---|---|
| `jotta doctor` | Required files, valid JSON, skill frontmatter and references, model routing, Orca availability |
| `jotta validate-prd` | Feature table, duplicate IDs, priorities and missing dependencies |
| `jotta gate text` | Forbidden dash characters in tracked text files |
| `jotta gate staged` | Local-only harness files and `.gitkeep` in the staging area |
| `jotta gate branch` | Branch name format |
| `jotta gate commit` | Conventional commit format and forbidden text such as AI attribution or planning IDs |
| `jotta quality <profile>` | The project's own commands from `gates.json`, with a compact receipt |
| `jotta budget check` | Budget thresholds; see [budget and routing](./budget-and-routing.md) |

`.jotta/sensors/computational/pre-commit-config.example.yaml` shows how to run the staged and text gates as pre-commit hooks.

### Compact receipts

`jotta quality` stores each command's full output under `.jotta/runtime/logs/` and writes a receipt to `.jotta/runtime/receipts/`. The receipt keeps the exit code and at most the configured number of lines, preferring lines that look like errors, and states how many lines were omitted. The model reads the receipt and opens the full log only when it needs to.

## Inferential sensors

Review rubrics live in `.jotta/sensors/inferential/`: spec, code, architecture, pull request and commit plan. The `final-qa` skill uses them for final or high-risk review. Reviewers are read-only, separate findings into blocking, important and suggestions, and need observable evidence for blocking findings.

## Human gates

`.jotta/policy/human-gates.md` lists the situations where the agent stops, records the blocker and asks for a decision. They include destructive database migrations, production deployment, paid external services, missing credentials, authentication, payment and personal data changes, force pushes, branch protection bypass, ambiguous requirements, PRD changes that affect completed features, unresolved merge conflicts, the budget threshold and an unavailable required model. An approval applies only to the gate it answers.
