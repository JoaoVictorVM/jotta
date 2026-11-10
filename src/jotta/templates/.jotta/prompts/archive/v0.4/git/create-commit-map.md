# Criar mapa de commits

## Prompt

```text
Analise todo o trabalho ainda nao publicado deste projeto e gere um mapa de commits usando `.harness/workflows/commit-roadmap.md` no modo `plan`.

Inclua alteracoes da working tree, arquivos ainda nao rastreados relevantes e commits locais ainda nao enviados, sem misturar essas categorias. Exclua segredos, caches, builds, dependencias e arquivos locais do harness.

Agrupe por mudanca logica, proponha Conventional Commits em pt-BR, registre fingerprints e salve os planos Markdown e JSON em `.planning/commit-plans/`.

Nao execute stage, commit, push, `git init` ou qualquer escrita no GitHub.
```
