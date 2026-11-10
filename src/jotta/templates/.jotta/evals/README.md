# Evals

Run these behavior cases after a structural change to the harness. Cases 001 to 011 preserve the original contracts. Cases 012 to 017 cover the v0.5 lean runtime, Orca lifecycle, compact quality evidence, profile routing, context discovery and final QA.

Automated structural checks:

```bash
python .harness/scripts/self_test.py
python .harness/scripts/harness.py doctor
```

Behavior cases remain human-readable because they test agent decisions across providers.
