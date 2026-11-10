# Implementar produto autonomamente com GitHub

## Prompt

```text
Execute o produto descrito em `.planning/PRD.md` usando o workflow autonomo com GitHub.

HARNESS_RUN: true
interaction: autonomous
destination: github
scope: product
prd: .planning/PRD.md

Esta mensagem autoriza o ciclo GitHub completo dentro desse escopo. Leia `AGENTS.md`, execute o doctor, valide o PRD e sincronize o estado. Processe features por waves e dependencias. Para cada feature, gere spec e plano, implemente, valide, crie checkpoints semanticos compactos, abra PR, faca review independente, corrija findings, aguarde checks e use merge commit.

Atualize o estado depois de cada transicao comprovada. Continue features independentes quando seguro. Pare somente em human gate, bloqueio global ou falta de autoridade. Nunca publique `.planning` ou `.harness`.
```
