---
version: 2
default: ask
allow:
  - read-project-files
  - edit-project-files
  - run-project-validation
  - update-local-planning
  - update-local-state
deny:
  - force-push
  - hard-reset
  - read-secrets
  - commit-secrets
  - deploy-production
  - bypass-branch-protection
profiles:
  autonomous-github:
    allow:
      - create-orca-worktree
      - open-visible-worker-terminal
      - create-branch
      - create-commit
      - push-branch
      - open-pr
      - merge-pr-with-merge-commit
      - remove-merged-worktree
      - delete-merged-local-branch
  autonomous-local:
    deny:
      - mutate-git
      - github-write
      - create-worktree
---

# Permissoes

Este arquivo restringe o que o harness pode executar automaticamente. Ele nao amplia permissoes da plataforma. A precedencia interna e `deny`, human gate, `allow`, `default`.

A limpeza de uma worktree so e permitida depois de merge confirmado, SHA registrado e verificacao de que a worktree esta limpa. O fluxo nunca usa remocao forcada.

Edite o frontmatter e execute `python .harness/scripts/harness.py doctor`.
