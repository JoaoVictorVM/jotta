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
- Replaces `scripts/self_test.py` with a pytest unit suite in `tests/unit/` for the budget guard, model routing, PRD parsing, task sync, state, risk and the Orca adapter.
- `jotta install` in a subdirectory of a Git repository now anchors the Git exclusions to that subdirectory, and the overwrite confirmation treats end of input as a no instead of failing.
- Runs the CI on Linux and Windows, including end-to-end tests of `jotta install` through the installed command.
- Splits the CI into lint, type checking and test jobs, runs the tests on Python 3.10 and 3.12, and requires 80% coverage.
- Adds the first architecture decision records in `docs/decisions/`.
- Adds `jotta hook pre-tool-use`, a Claude Code hook that blocks force pushes, hard resets, branch protection bypasses, secret reads and recursive deletions outside the project, and logs each block to `.jotta/runtime/logs/hooks.jsonl`.
- Records the files a task may edit in the context packet, from the spec and `jotta prepare --allow`. The hook blocks edits outside them in `strict`, warns in `lean`, and only a person can widen the scope with `jotta scope allow`.
- Adds `jotta hook post-tool-use`, which runs the `smoke` quality profile after a code edit, at most once per debounce window, and feeds the compact receipt of a failure back to the agent.
- Adds `jotta hook stop`, which keeps the agent from ending its turn while the active task lacks a passing quality receipt of its profile's gate written after the last code edit.
- Adds `jotta adapter claude`, also run by `jotta install`, which generates `.claude/settings.json` with the Jotta hooks, a subagent per harness role with read-only tools for the reviewers, and a skill entry per harness skill, merging with existing files without overwriting them. `jotta doctor` warns when the hooks are missing.
- Adds `jotta detect-stack`, also run by `jotta install`, which recognizes Node (npm, pnpm, yarn), Python (uv, poetry, pip), Go and Rust and fills the `smoke`, `feature` and `full` quality profiles without overwriting profiles the user edited. `jotta doctor` warns when a profile can be filled or has no commands.
- The PRD excerpt in a task's context packet now keeps only the feature's own table row, section, list items and paragraphs, so a neighboring feature no longer raises the task's risk or enters its context.
- Adds `jotta adapter codex`, also run by `jotta install`, which generates `.codex/hooks.json`, `.codex/config.toml`, a custom agent per harness role and skill entries under `.agents/skills/`. `jotta hook` gains `--agent codex`, which answers in the Codex hook protocol and checks every file of an `apply_patch`. The installer adds `.codex/` and `.agents/` to the Git exclusions.
- Adds `jotta adapter opencode`, also run by `jotta install`, which generates `.opencode/opencode.jsonc` with permission rules from the policy deny list, a subagent per harness role and skill entries under `.opencode/skills/`. The installer adds `.opencode/` to the Git exclusions.
- Adds `.jotta/policy/profile-permissions.json`, with the shell commands `lean`, `strict` and `manual-classic` allow, ask about or deny. The Claude Code, Codex and OpenCode adapters apply the profile set in `config.yaml`, or the one passed with `--profile`, and `jotta doctor` warns when a generated configuration is out of date.
- The hooks read the quality gates from `HEAD` when they are committed, or from a snapshot taken at the start of the agent session, so an uncommitted edit to `gates.json` does not change the checks until it is committed or a new session starts. A receipt counts at `Stop` only when it ran the pinned commands. The first hook of a session and `jotta doctor` warn when the file on disk differs.
- Adds `jotta usage`, which reads the local Claude Code and Codex session transcripts and reports input, output, cache read and cache creation tokens per model, agent and task, priced with the new `.jotta/policy/pricing.json`. `jotta prepare`, `checkpoint` and `finish` record the task periods it uses.
- `jotta prepare` and `jotta checkpoint` measure the run's usage from the agent transcripts and store it in `usage.json` with `measurement: measured`, and the budget guard decides with it. The recorded estimates remain the fallback when nothing can be measured.
- `jotta status` shows a table of the run's measured tokens, cache and cost per feature and stage, and the budget decision; `--json` prints the full status. It printed JSON before, so scripts must add `--json`. Task periods record the stage of the prepared role.
- Adds an optional OpenTelemetry export: `jotta export-trace`, and `jotta finish` when `telemetry.otel.enabled` is set, send the run's measured usage as an OTLP/HTTP trace with spans per run, feature, stage and model. It is off by default.

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
