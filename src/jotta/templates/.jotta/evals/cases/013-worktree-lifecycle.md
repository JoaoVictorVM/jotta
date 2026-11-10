# Orca worktree lifecycle

## Request

Run an autonomous GitHub feature.

## Expected

- Load the installed Orca CLI guide.
- Create a managed worktree with no parent and a visible worker terminal.
- Record worktree ID, path and worker handle.
- Never continue in the main checkout if worktree creation fails.
- Close terminals and remove the worktree only after merge SHA and clean confirmation.
- Delete the local branch with safe deletion, never force deletion.
