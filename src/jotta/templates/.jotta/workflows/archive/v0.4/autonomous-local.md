# Workflow: produto autonomo local

## Entrada

PRD e autorizacao explicita para execucao autonoma local.

## Restricoes

- Nao criar ou alterar branch.
- Nao criar commit.
- Nao fazer push.
- Nao abrir ou editar PR.
- Nao acessar GitHub para escrita.
- Nao executar `git init`.

Comandos Git de leitura podem ser usados quando o repositorio existir.

## Fluxo

1. Execute preflight sem exigir Git ou GitHub.
2. Verifique o budget em `before-feature` e resolva as rotas de modelo.
3. Sincronize tarefas do PRD.
4. Selecione a proxima feature desbloqueada.
5. Gere spec e plan com a rota `efficient`.
6. Implemente sequencialmente. Use agentes extras somente para leitura, investigacao ou review, com reserva previa de budget.
7. Rode gates `fast` e `feature`.
8. Verifique o budget e revise em contexto separado usando arquivos alterados e evidencias.
9. Registre consumo, snapshot de hashes e marque `completed-local`.
10. Repita ate concluir o escopo.
11. Execute a validacao integrada final.

## Conclusao

Todas as tarefas do escopo estao `completed-local`, com evidencia de testes. Nenhum estado Git foi modificado.

