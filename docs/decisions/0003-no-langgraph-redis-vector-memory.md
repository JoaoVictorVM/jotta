# 0003: Do not adopt an orchestration framework, external store or vector memory

- Status: Accepted
- Date: 2026-11-14

## Context

Agent applications are often built on LangChain or LangGraph, keep short-term memory in Redis, add long-term memory with mem0 and retrieve context through RAG over a vector store. These are reasonable choices for a product that owns its agent loop.

Jotta does not own the agent loop. It wraps agents that already exist (Claude Code, Codex, OpenCode) and steers them through files, commands and gates. Those agents already plan, call tools, read the repository and keep their own conversation memory. The harness adds structure around them: workflows, profiles, specs, state, budget, model routing and checks.

## Decision

The runtime has no third-party dependencies and adopts none of these components.

- **Orchestration** stays with the host agent. Jotta describes the workflow in Markdown and enforces the deterministic parts through the `jotta` command.
- **Short-term state** is the JSON run state of [0001](./0001-json-as-source-of-truth.md), not a Redis instance.
- **Long-term memory** is curated Markdown in `.jotta/memory/`, written only when a learning is reusable and backed by project evidence, not inferred automatically.
- **Retrieval** is exact: the agent searches the repository with its own tools, and `jotta prepare` builds a compact context packet from the PRD excerpt, the spec and the plan. There is no embedding index.

## Alternatives

- **LangGraph for the workflow.** Would make the state machine explicit, but forces a Python runtime loop that competes with the host agent's own loop and ties every project to one framework. Rejected.
- **Redis for short-term memory.** Needs a running server and credentials, and solves a problem that small JSON files already solve. Rejected.
- **mem0 or another automatic memory.** Inferred memories are hard to audit and can preserve wrong facts. Curated memory is slower to build but reviewable in a pull request. Rejected.
- **RAG over the codebase.** Coding agents already search code precisely with grep and file reads. A vector index adds staleness, chunking errors and an embedding provider. Rejected for code. Revisit for large external documentation.

## Consequences

- `pip install` brings only Jotta, and the harness works offline on any operating system.
- Every piece of state and memory is a file a person can read and review.
- Jotta inherits the strengths and limits of the host agent. It cannot run its own multi-step graph or coordinate agents outside what the host and Orca provide.
- Observability comes from structured logs and receipts written by the command, not from a framework's tracing. Exporting traces to a tool such as Langfuse remains possible as an optional integration.
- Revisit if Jotta grows its own agent loop, or if evals show that exact search misses context that retrieval would find.
