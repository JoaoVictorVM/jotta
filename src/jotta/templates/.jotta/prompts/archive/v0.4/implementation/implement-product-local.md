# Implementar produto somente local

## Prompt

```text
Execute o produto descrito em `.planning/PRD.md` usando o workflow autonomo local.

HARNESS_RUN: true
interaction: autonomous
destination: local
scope: product
prd: .planning/PRD.md

Leia `AGENTS.md`, valide o PRD e sincronize o estado. Processe features por waves e dependencias, gere specs e planos, implemente, revise e execute todas as validacoes.

Nao crie ou altere branch, stage, commit, push, PR ou merge. Nao execute `git init` e nao escreva no GitHub. Atualize apenas os artefatos locais permitidos. Pare somente em human gate ou bloqueio sem recuperacao segura.
```
