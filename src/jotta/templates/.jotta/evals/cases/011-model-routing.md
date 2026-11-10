# Caso 011: roteamento de modelos

## Objetivo

Validar selecao por tarefa sem reduzir contratos das skills.

## Cenarios

1. Execute `model_router.py validate`.
2. Resolva `spec-writer` e confirme tier `efficient`.
3. Resolva `implement-feature` e confirme tier `strong`.
4. Resolva `pr-reviewer` e confirme tier `review`.
5. Com modelo nulo e politica `inherit`, confirme modelo herdado sem falsa alegacao de troca.
6. Configure um ID valido do provedor e confirme retorno `resolved`.
7. Simule plataforma sem selecao por agente e confirme registro do modelo efetivo herdado.
8. Confirme que trocar modelo nao remove entrevista, validacao, review ou human gates.

## Aprovacao

Toda criacao de agente registra task, tier, preferencia, modelo efetivo e origem da decisao.
