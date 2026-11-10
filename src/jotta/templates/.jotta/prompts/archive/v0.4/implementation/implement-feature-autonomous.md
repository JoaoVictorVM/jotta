# Implementar feature autonomamente

## Prompt

```text
Implemente completamente a feature `[FEATURE]` usando o harness.

HARNESS_RUN: true
interaction: autonomous
destination: github
scope: feature
prd: .planning/PRD.md

Esta mensagem autoriza o ciclo GitHub definido para esse escopo. Leia `AGENTS.md`, permissoes e human gates. Gere a spec se ainda nao existir, implemente, valide, crie checkpoints semanticos compactos, abra o PR, faca review independente, corrija findings bloqueantes, confirme checks e finalize com merge commit.

Pare somente em human gate, bloqueio sem recuperacao segura ou falta de autoridade. Nunca publique `.planning` ou `.harness`.
```
