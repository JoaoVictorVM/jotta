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

# Permissions

This file restricts what the harness may run automatically. It never extends the platform's permissions. The internal precedence is `deny`, human gate, `allow`, then `default`.

Cleaning up a worktree is allowed only after a confirmed merge, a recorded SHA and a check that the worktree is clean. The flow never uses forced removal.

Edit the frontmatter and run `jotta doctor`.
