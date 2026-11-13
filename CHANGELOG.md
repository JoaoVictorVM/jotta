# Changelog

All notable changes to this project are recorded here.

## Unreleased

- Ships Jotta as a Python package with the `jotta` command, which replaces the scripts in `.harness/scripts/`.
- Moves the installed content into the package templates and renames the harness folder from `.harness/` to `.jotta/`.
- Consolidates permissions, budget and routing in `.jotta/policy/` and creates the run state on demand in `.jotta/runtime/state/`.
- Replaces `scripts/install.py` and `bootstrap.py` with `jotta install`, with `--dry-run`, `--force-overwrite` and `--no-git-exclude`.
- `doctor` no longer requires local Git excludes or state files.
- Moves the architecture and the agent assumptions to `docs/`, adds the concept guides and merges the release notes into this changelog.
- Removes the archived v0.4 prompts and workflows. They remain available in the `v0.5.0` tag, under `.harness/prompts/archive/v0.4/` and `.harness/workflows/archive/v0.4/`.
- Writes the installed content, the CLI messages and the eval cases in English. The language of commits and documentation is configurable in `.jotta/config.yaml`.

## 0.5.0

- Adds the `manual-classic`, `lean` and `strict` profiles.
- Fully preserves the contracts of the PRD, spec and implementation skills.
- Consolidates execution into product, change and quality workflows.
- Adds progressive context, checkpoints and compact quality receipts.
- Adds a budget gate and per-task model routing.
- Adds worktrees and visible sessions managed by Orca.
- Adds adapters for Codex, Claude and OpenCode.
- Adds prompts, evaluations and automated checks.
- Prepares the project for open source distribution under the MIT license.
- Uses smoke checks per feature in the lean profile and concentrates the semantic review at the end.
- Removes the worktree and the local branch only after a confirmed merge and safety checks.
- Records consumption estimates per phase and treats provider limits as a human gate when the platform exposes them.
- Keeps the old prompts and workflows in `archive/v0.4` for reference, outside the normal context.

### Compatibility

The `manual-classic` profile is the compatibility track for the previous flow, including interviews, G1 to G4, plans, detailed validation and commits according to the preserved contract. The `strict` profile reuses the full contract with automation. The `lean` profile is the new economical default.

### Known limitation

The Orca adapter needs the `orca` or `orca.exe` executable in the environment where the harness runs. `doctor` reports when it is not reachable.
