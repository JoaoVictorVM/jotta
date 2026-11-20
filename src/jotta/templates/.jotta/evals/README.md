# Evals

Run these behavior cases after a structural change to the harness. Cases 001 to 011 preserve the original contracts. Cases 012 to 021 cover the v0.5 lean runtime, Orca lifecycle, compact quality evidence, profile routing, context discovery, final QA, the task edit scope, the quality receipt required to stop, the Claude Code subagents and the Codex hooks.

Automated structural checks:

```bash
jotta doctor
jotta models validate
```

Behavior cases remain human-readable because they test agent decisions across providers.
