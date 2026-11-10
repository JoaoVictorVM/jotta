# Biblioteca de prompts

Estes arquivos sao pontos de entrada para o harness. Eles declaram objetivo, escopo, perfil e destino, mas nao repetem regras operacionais.

## Como usar

1. Escolha o prompt mais proximo do objetivo.
2. Substitua somente os campos entre colchetes.
3. Copie o bloco `Prompt` inteiro para a IA na raiz do projeto.
4. Quando um caminho ou ID nao se aplicar, remova a linha correspondente.

As fontes de verdade continuam sendo `AGENTS.md`, `.harness/AGENT-MANUAL.md`, workflows, skills, permissoes, human gates e estado. Em caso de divergencia, o prompt nunca prevalece sobre essas fontes.

## Indice

| Objetivo | Arquivo |
|---|---|
| Criar PRD | `planning/create-prd.md` |
| Revisar PRD | `planning/revise-prd.md` |
| Criar spec de uma feature | `planning/create-feature-spec.md` |
| Criar specs de uma wave | `planning/create-wave-specs.md` |
| Implementar feature supervisionada | `implementation/implement-feature-supervised.md` |
| Implementar feature autonomamente | `implementation/implement-feature-autonomous.md` |
| Implementar produto com GitHub | `implementation/implement-product-autonomous.md` |
| Implementar produto somente local | `implementation/implement-product-local.md` |
| Corrigir bug local | `maintenance/fix-bug-local.md` |
| Corrigir bug com GitHub | `maintenance/fix-bug-github.md` |
| Adicionar feature | `maintenance/add-feature.md` |
| Fazer refatoracao | `maintenance/refactor.md` |
| Planejar commits | `git/create-commit-map.md` |
| Aplicar mapa de commits | `git/apply-commit-map.md` |
| Retomar execucao | `operations/resume-run.md` |
| Diagnosticar projeto | `operations/diagnose-project.md` |

## Campos comuns

- `[IDEIA]`: descricao livre do produto.
- `[FEATURE]`: ID, nome ou caminho da feature.
- `[WAVE]`: numero ou nome da wave.
- `[PROBLEMA]`: comportamento observado.
- `[COMPORTAMENTO_ESPERADO]`: resultado correto.
- `[ESCOPO]`: limites da execucao.
- `[CAMINHO_DO_PLANO]`: arquivo JSON ou Markdown de commit plan.

Um prompt inicia o fluxo. O workflow define a sequencia, a skill define como executar, o agente define responsabilidade, as permissoes definem autoridade e o estado permite retomar.
