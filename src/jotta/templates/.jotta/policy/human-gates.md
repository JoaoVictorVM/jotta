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

When a listed condition occurs, stop before acting, record the blocker in the state and present the decision that is needed. An approval applies only to the gate it answers.

