# Corrigir bug localmente

## Prompt

```text
Corrija o problema abaixo usando o fluxo de change intake e bugfix do harness.

interaction: autonomous
destination: local
scope: change

Problema observado:
[PROBLEMA]

Comportamento esperado:
[COMPORTAMENTO_ESPERADO]

Reproduza a falha antes de editar, determine a causa, crie teste de regressao quando aplicavel, implemente a menor correcao segura e execute as validacoes completas. Nao altere Git nem GitHub. Se o relato mudar requisito em vez de corrigir um bug, reclassifique e pare no gate apropriado.
```
