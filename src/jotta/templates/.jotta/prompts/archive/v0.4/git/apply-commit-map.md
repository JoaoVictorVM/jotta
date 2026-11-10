# Aplicar mapa de commits

## Prompt

```text
Aplique o mapa de commits localizado em `[CAMINHO_DO_PLANO]` usando `.harness/workflows/commit-roadmap.md` no modo `apply`.

Publicacao: [sem push ou com push]

Valide fingerprints antes de qualquer mutacao. Se houver drift, pare e solicite um novo plano. Stage cada arquivo explicitamente, execute o gate de commit e crie os commits na ordem aprovada.

Nao inclua segredos nem arquivos de `.harness` ou `.planning`. Nao crie repositorio remoto sem nome, visibilidade e autorizacao explicitos.
```
