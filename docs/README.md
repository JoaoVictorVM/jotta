# Documentation

## Concepts

- [Architecture](./concepts/architecture.md): the package, the installed harness and the principles behind them.
- [Workflows](./concepts/workflows.md): how product, change and quality requests are handled.
- [Profiles](./concepts/profiles.md): `manual-classic`, `lean` and `strict`, and when each one applies.
- [Guides and sensors](./concepts/guides-and-sensors.md): what steers the agent before it acts and what checks it afterwards.
- [State machine](./concepts/state-machine.md): runtime files, run and task states, and evidence.
- [Budget and routing](./concepts/budget-and-routing.md): budget gates and model selection.
- [OpenTelemetry export](./concepts/opentelemetry.md): a run's measured usage as a trace, with Langfuse and Claude Code setup.
- [Hooks](./concepts/hooks.md): the checks that run before each tool call and block forbidden actions.
- [Claude Code adapter](./concepts/claude-code.md): the settings, subagents and skills generated under `.claude/`.
- [Codex adapter](./concepts/codex.md): the hooks, config, agents and skills generated for Codex, and the parity with Claude Code.
- [OpenCode adapter](./concepts/opencode.md): the permission rules, subagents and skills generated for OpenCode, and what it does not enforce.
- [Model assumptions](./model-assumptions.md): why each mechanism exists and when to revisit it.

## Design decisions

- [Decision records](./decisions/README.md): why run state is JSON, why `lean` is the default, why there is no orchestration framework or vector memory, and why pull requests use merge commits.

## Project

- [Publishing](./PUBLISHING.md)
