---
version: 1
gates:
  - destructive-database-migration
  - production-deployment
  - paid-external-service
  - missing-credential
  - authentication-model-change
  - payment-flow-change
  - personal-data-handling
  - force-push
  - branch-protection-bypass
  - ambiguous-product-requirement
  - prd-change-affecting-completed-feature
  - unresolved-merge-conflict
  - provider-budget-threshold
  - required-model-unavailable
---

# Human gates

Ao encontrar uma condicao listada, pare antes da acao, registre o bloqueio no estado e apresente a decisao necessaria. Uma aprovacao vale somente para o gate apresentado.

