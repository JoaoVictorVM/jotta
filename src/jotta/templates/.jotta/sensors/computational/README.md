# Computational sensors

Run them through the `jotta` command.

- `doctor`: harness integrity.
- `validate-prd`: feature table, duplicate IDs, priorities and missing dependencies.
- `gate text`: forbidden dash characters in tracked text files.
- `gate staged`: local-only harness files and `.gitkeep` in the staging area.
- `gate branch`: branch name format.
- `gate commit`: message format and forbidden text.
- `quality`: the commands configured for each profile.
- `budget check`: budget thresholds, see `provider-budget.md`.
