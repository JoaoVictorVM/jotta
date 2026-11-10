# Workflow: produto autonomo com GitHub

## Entrada

PRD em `.planning/PRD.md` e autorizacao explicita para modo autonomo com GitHub.

## Fluxo

1. Execute `doctor`, valide PRD e sincronize `tasks.json`.
2. Leia permissoes e human gates.
3. Verifique o budget em `before-feature` e resolva as rotas de modelo.
4. Selecione features `ready` em ordem de wave e dependencias.
5. Execute Foundation Features sequencialmente.
6. Antes de agentes paralelos, reserve o consumo previsto e verifique novamente o budget.
7. Para features independentes, use worktrees separadas somente quando houver escritores simultaneos.
8. Gere spec e plan da feature atual com `spec-writer` na rota `efficient`.
9. Revise a spec em contexto separado.
10. Implemente com `implement-feature` no perfil `autonomous`, destino `github`.
11. Use de 1 a 3 commits semanticos por feature, com limite normal de 5.
12. Verifique o budget em `before-review`, abra PR e execute `pr-reviewer` na rota `review`.
13. Devolva achados bloqueantes ao implementador por no maximo duas rodadas.
14. Espere checks obrigatorios verdes.
15. Faca merge commit, nunca squash ou rebase merge.
16. Confirme o merge, registre consumo observado, libere reservas e atualize estado.
17. Repita ate concluir o escopo ou ficar bloqueado.

## Paralelismo

Um escritor por worktree. Nao paralelize Foundation Features ou features que alterem os mesmos arquivos centrais. Agentes de leitura e review podem operar em paralelo.

## Falhas

Marque a feature como `blocked` apos o limite. Continue features independentes se configurado. Pare quando o bloqueio impedir todas as tarefas restantes.

## Conclusao

Todas as features do escopo estao `merged`, os testes finais foram executados e o estado foi atualizado.

