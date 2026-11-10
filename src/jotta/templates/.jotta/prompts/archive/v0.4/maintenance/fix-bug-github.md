# Corrigir bug e publicar no GitHub

## Prompt

```text
Corrija e publique o problema abaixo usando o fluxo de change intake e bugfix do harness.

HARNESS_RUN: true
interaction: autonomous
destination: github
scope: change

Problema observado:
[PROBLEMA]

Comportamento esperado:
[COMPORTAMENTO_ESPERADO]

Reproduza a falha, identifique a causa, crie teste de regressao quando aplicavel e implemente a menor correcao segura. Valide, crie checkpoints semanticos compactos, abra PR, faca review independente, corrija findings, confirme checks e use merge commit. Se houver mudanca de requisito, reclassifique antes de implementar.
```
