# Workflow: mapa de commits

## Modo plan

1. Classifique o projeto como `working-tree`, `unpublished-history` ou `initial-project`.
2. Exclua segredos, caches, dependencias, builds e artefatos locais do harness.
3. Separe alteracoes nao commitadas de commits locais ainda nao enviados.
4. Agrupe arquivos por mudanca logica. Um arquivo pertence a um commit no MVP.
5. Gere Markdown e JSON em `.planning/commit-plans/`.
6. Inclua fingerprint de cada arquivo e do estado Git.
7. Nao crie commits.

## Modo apply

1. Leia um plano existente.
2. Recalcule fingerprints. Se houver drift, pare e solicite novo plano.
3. Inicialize Git somente se autorizado e necessario.
4. Stage arquivos explicitamente por commit.
5. Rode o gate `commit` e crie os commits na ordem.
6. Faca push somente quando solicitado.
7. Criar repositorio GitHub exige nome e visibilidade explicitos.

