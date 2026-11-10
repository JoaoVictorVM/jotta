# Workflow: extensao do produto

1. Analise impacto sobre features, contratos e dependencias existentes.
2. Copie o PRD atual para `.planning/archive/` antes da alteracao.
3. Adicione a nova feature com o proximo ID disponivel. Nunca renumere IDs antigos.
4. Atualize dependencias, waves e criterios de integracao.
5. Sincronize `tasks.json`, preservando estados por ID.
6. Gere spec e plan somente para a nova feature e para artefatos comprovadamente invalidados.
7. Execute o workflow de feature escolhido.

