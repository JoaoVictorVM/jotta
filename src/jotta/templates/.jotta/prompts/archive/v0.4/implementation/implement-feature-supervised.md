# Implementar feature supervisionada

## Prompt

```text
Implemente a feature `[FEATURE]` usando o harness.

HARNESS_RUN: true
interaction: supervised
destination: github
scope: feature
prd: .planning/PRD.md

Leia `AGENTS.md`, use `.harness/workflows/supervised-github.md` e preserve o contrato completo da skill `implement-feature`. Pare nos gates de branch, implementacao, publicacao e merge. Use checkpoints semanticos compactos, execute todas as validacoes, apresente o checklist manual e use merge commit, nunca squash ou rebase merge.
```
