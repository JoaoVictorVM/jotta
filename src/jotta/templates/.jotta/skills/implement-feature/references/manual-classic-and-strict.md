---
name: implement-feature
description: Implements a feature from its spec and plan with exhaustive validation, progress tracking, Conventional Commits in pt-BR and acceptance-criteria reporting. Preserves the original supervised GitHub workflow and supports explicit harness profiles for autonomous GitHub and local-only execution.
---

# Implement Feature

## HARNESS EXECUTION PROFILES

This section extends the original skill without removing its implementation, validation, reporting, resume, review or edge-case contracts.

### Compatibility rule

A direct invocation without a harness execution envelope uses the original supervised GitHub workflow below, including G1 to G4 and atomic commits. This preserves the established manual workflow exactly.

A harness profile activates only when `product-orchestrator` supplies all of these fields: `HARNESS_RUN`, `interaction`, `destination`, exact planning paths and authorized scope. A partial or ambiguous envelope falls back to the original supervised GitHub workflow.

| Profile | Git and GitHub behavior | Approval behavior | Commit behavior |
|---|---|---|---|
| direct invocation | Original branch, push, PR, review and merge flow | Original G1 to G4 | Original atomic commits |
| `supervised + github` | Original GitHub flow | Original G1 to G4 | Compact semantic checkpoints by default; atomic remains available |
| `autonomous + github` | Branch, push, PR, independent review, CI check and merge commit | Initial run authorization covers G1 to G4; human gates still stop the run | Compact semantic checkpoints |
| `supervised + local` | No branch, commit, push, PR or merge | Ask once before writing code; human gates still apply | No commits |
| `autonomous + local` | No branch, commit, push, PR or merge | Initial run authorization covers implementation; human gates still apply | No commits |

### Precedence and safety

- This section overrides Git mutations, approval prompts and commit scheduling only when a complete `HARNESS_RUN` envelope is present.
- Requirements, dependency checks, lazy codebase reading, progress tracking, phase validation, runtime exercise, retry classification, Final Verification, Component Overview walk-through, AC re-check, deviations, soft-fails, pre-existing failures, manual test checklist and edge cases always remain in force.
- Human gates in `.harness/permissions/human-gates.md` override autonomous authorization. Stop before the gated action and resume only after a human decision.
- `.planning/` and `.harness/` are local-only. Never stage, commit, push or mention their contents in versioned or GitHub content. Keep them out through `.git/info/exclude`.
- GitHub profiles always use merge commits. Never use squash merge or rebase merge.
- Local profiles may run inside a Git repository, but they must not mutate Git state or contact GitHub.

### Compact semantic checkpoints

In harness GitHub profiles, implementation units remain the smallest units of work and validation, but they are not automatically commits.

- Target 1 to 3 meaningful commits per feature, with a soft cap of 5 when separation materially improves review or rollback.
- Group related code, tests and supporting changes into buildable semantic checkpoints. Do not create one commit per file, function or plan step.
- Stage every file explicitly and apply all Versioned-content checks to every commit.
- Before the first push, a correction may be folded into its semantic checkpoint when safe. After push, use a new fix commit and do not rewrite published history.
- The original atomic strategy remains available for direct invocations and as an explicit supervised override.

### Autonomous GitHub review

After opening the PR, an autonomous GitHub run performs a fresh review of the complete diff against the acceptance criteria, runs or verifies required checks, fixes actionable findings, pushes fixes and repeats review until no blocking finding remains. Merge only when the PR is open and mergeable, required checks pass, the versioned-content audit passes and no human gate is pending. Record evidence in the local progress log, then merge with `--merge`.
Implement a feature from its existing `spec.md` + `plan.md` through a pull-request workflow. The skill reads the feature's technical specification and implementation plan, creates a branch, writes the code phase by phase, validates each phase, commits each change atomically, opens a pull request, waits for the user to review it on GitHub, and merges only after explicit approval.

Workflow at a glance:

| # | Stage | Who |
|---|-------|-----|
| 1 | Create the branch | Claude (after approval) |
| 2 | Implement and commit atomically | Claude (after approval) |
| 3 | Open the PR | Claude (after approval) |
| 4 | Review the PR on GitHub | User |
| 5 | Merge | Claude (after approval) |

If the project has its own `CLAUDE.md`, its rules take precedence for anything this skill does not cover (code comments, folder conventions, etc.).

## INPUT

Free-form. The skill figures out what was passed. Any combination works:

- A feature identifier: `F09`, `Video Upload`, or similar.
- A feature folder: `.planning/features/F09-in-video-transcription-search/`, `docs/F09-in-video-transcription-search/`, `./F09/`, etc.
- A file inside the feature folder: `.planning/features/F09-in-video-transcription-search/spec.md` or `docs/F09-in-video-transcription-search/spec.md`.
- A PRD path: `@.planning/PRD.md`, `.planning/PRD.md`, `@docs/PRD.md`, `docs/PRD.md`, `@PRD.md`.
- Extra natural-language instructions appended anywhere (see **Overrides**).

The skill only needs to locate two files and one reference source:

1. **`spec.md` and `plan.md`** for the target feature. If the input points to a folder, look inside. If it points to a file, look in its parent folder. If it points to an ID or name, search under `.planning/features/` first, then the original fallback locations such as `docs/`, for a folder matching `<ID>-*` or whose name kebab-cases to the given name.
2. **The PRD**. If explicitly passed, use it. Otherwise, auto-discover: `.planning/PRD.md` -> `docs/PRD.md` -> `PRD.md` -> any top-level `*.md` whose content reads like a product spec. If none found, abort. If multiple are plausible, abort and list them.

## OUTPUT

- **Branch**: one new branch per feature, created from the up-to-date base branch.
- **Commits**: direct invocation keeps the original atomic strategy. Harness GitHub profiles use compact semantic checkpoints. Harness local profiles create no commits.
- **Pull request**: opened on GitHub against the base branch, merged with a merge commit after the user approves.
- **`progress.md`**: a local-only progress log inside the feature folder (see **Progress log**). It is the only file the skill writes besides code changes.
- **Chat report** at the end of implementation: the feature's acceptance-criteria checklist marked ✓ / ✗ / ○ against actual test results, sections for Deviations, Soft-fails, Pre-existing failures, Overrides applied, Overrides ignored and Phase status, plus a manual test checklist for the user.

---

## VERSIONED-CONTENT RULES

"Versioned content" means everything that ends up in git or on GitHub: branch names, commit messages, PR titles, PR descriptions, review comments, code, code comments and any committed file. These rules are absolute and cannot be overridden.

1. **No dashes.** Never use an em dash (-) or en dash (-) anywhere in versioned content or in chat messages. Use a comma, a colon or parentheses instead. Plain hyphens inside identifiers (`feat/busca-video`, `kebab-case`) are fine.
2. **No planning references.** PRD, spec and plan exist only locally. Never mention them or their IDs in versioned content: no `F01`, `F09`, `P2`, `RF02`, `US03`, no "resolve F01", "conforme a spec", "ver PRD", "phase 2 of the plan". Describe a change by what it does, never by the document it came from. IDs are allowed only in chat and in `progress.md`.
3. **No AI attribution.** Never add `Co-Authored-By: Claude <noreply@anthropic.com>`, any other `Co-Authored-By` line naming Claude or Anthropic, "Generated with Claude Code", or any mention of Claude, Anthropic or AI in commits, PRs, comments or descriptions. Nothing in the repository or on GitHub may show that Claude took part.
4. **Conventional Commits in pt-BR.** Format `tipo(escopo): descrição`. Description in lowercase, verb in the present tense, no trailing period. Types: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `perf`, `build`, `ci`, `chore`. The scope is the module or area touched (`backend`, `api`, `frontend`, `db`, `auth`, ...), never a feature or phase ID. Examples:
   - `feat(backend): implementa autenticacao`
   - `fix(frontend): corrige validacao do formulario de login`
   - `refactor(api): extrai logica de paginacao`
   Match the project's recent history if it already follows this format with its own conventions (scopes, accents); otherwise use exactly the format above.
5. **Branch names**: `tipo/descricao-curta` in pt-BR kebab-case, derived from what the feature does, never from its ID. Example: feature folder `F09-in-video-transcription-search` → `feat/busca-transcricao-video`.
6. **Explicit staging.** Stage files one by one (`git add <file>`). Never `git add -A`, `git add .` or `git commit -a`.
7. **AI and planning files stay local.** `CLAUDE.md`, `.claude/`, the PRD and the feature folders (spec, plan, `progress.md`) never get committed. Keep them out of git through `.git/info/exclude`, never through `.gitignore`, and never mention them in README, docs, code or any versioned file.

### Text check (mandatory)

Before every commit, before opening the PR and before posting any comment on GitHub, check the exact text that will be written (commit message including body and trailers, branch name, PR title, PR body, comment) against these patterns, case-insensitive:

- `-` or `-`
- `\bF\d+\b`, `\bP\d+\b`, `\bRF\d+\b`, `\bUS\d+\b`
- `\bPRD\b`, `\bspec\b`, `plan\.md`, `spec\.md`
- `Co-Authored-By`, `Claude`, `Anthropic`, `Generated with`, `\bIA\b`, `\bAI\b`

Any match → rewrite the text and check again. Never write versioned content that fails this check. After each commit, read it back with `git log -1 --format=%B` and confirm no trailer was appended by tooling; if one was, amend that commit's message immediately (it has not been pushed yet) and record it under `Deviations`.

---

## APPROVAL GATES

Ask for approval with the AskUserQuestion tool, in the user's language, so the user can answer with a button. Proceed only on an explicit yes. Each approval covers only its own gate and does not carry over to the next one or to a future run.

| Gate | When | Example question | Covers |
|------|------|------------------|--------|
| G1 | Before creating the branch | "Posso criar a branch `feat/busca-transcricao-video` a partir de `main`?" | Fetching and creating/checking out the branch |
| G2 | Before writing any code | "Posso implementar as 3 fases e commitar atomicamente na branch `feat/busca-transcricao-video`?" | All implementation and all atomic commits of this run, including fix commits from validation retries |
| G3 | After the final report, before pushing | "Posso fazer push e abrir o PR `feat(busca): adiciona busca na transcricao do video`?" (show the title and body) | Pushing the branch and creating the PR |
| G4 | After the PR is open | "Revisou o PR #12? Posso fazer o merge?" | Merging that PR |

Gates are part of the immutable core: no override can skip them. A "no" at any gate stops the run there and goes straight to the report with what was done so far.

---

## PROGRESS LOG

`progress.md` lives inside the feature folder (next to `spec.md`), so it is excluded from git together with the folder. It replaces any commit-message tagging: commit messages never carry feature or phase IDs. Format:

```
# Progress (local only)

Branch: feat/busca-transcricao-video
Base: main
PR: <url, once opened>
Status: in progress | locally complete | PR open | merged

## Phase 1: <phase name>
- [x] <atomic unit> (<short sha>)
- [x] <atomic unit> (<short sha>)
- [ ] <atomic unit>

## Phase 2: <phase name>
- [ ] <atomic unit>
```

Update it after each completed unit and validation gate. In GitHub profiles, add the checkpoint sha after each commit and update it when the PR opens or merges. In local profiles, mark completed units without a sha and finish with `Status: locally complete`. It is never staged.

---

## EXECUTION STEPS

### Step 1: Resolve Input

Parse the entire input as free-form. Extract:

- **Feature reference**: the first token that resolves to a folder containing `spec.md` + `plan.md`. Matches: ID patterns like `F\d+`, folder paths, file paths (parent folder = target), feature names (kebab-case + fuzzy match under `.planning/features/` first, then `docs/`).
- **PRD reference**: an explicit `*.md` path prefixed with `@` or written literally; if it looks like a PRD (product spec content at the top), accept it. Otherwise auto-discover.
- **Extra instructions**: any remaining text that isn't a path/ID/name. Treat it as natural-language overrides (Step 3).

If resolution fails:

- No `spec.md` or `plan.md` in the resolved folder → abort: "spec.md/plan.md missing in `<folder>`."
- No PRD found → abort: "No PRD found. Pass the path explicitly."
- Multiple plausible PRDs → abort and list candidates.
- Ambiguous feature reference (multiple folders match) → abort and list candidates.

### Step 2: Load Context

Read in full:

- `spec.md` of the target feature: Component Overview, Data Model, API Contracts, Business Rules, UX Flows, Error Handling, Testing Strategy, Assumptions/Decisions.
- `plan.md`: phases and steps in order.
- `progress.md`, if it exists (a previous run of this feature).
- **The PRD's acceptance-criteria content for this feature**. Locate it semantically, not by section number. Typical headings: "Acceptance Criteria", "Critérios de Aceitação", "AC". Typical shape: a checkbox list `- [ ]` scoped to the feature (by ID or name). Also locate any cross-feature/integration checklist that references this feature. Do NOT assume a fixed section number; find content by its shape.

If the PRD has no acceptance-criteria content for this feature, proceed with an empty AC checklist and note it under soft-fails.

Do NOT explore the codebase eagerly. Open files lazily as each phase requires them.

### Step 3: Apply Overrides

Interpret extra instructions as natural-language overrides on the defaults:

| Default | Example overrides |
|---|---|
| Hard-fail retry limit = 3 | "no retry limit", "max 5 tries" |
| Autonomous between G2 and G3 | "pause between phases": after each phase, ask with AskUserQuestion whether to continue |
| Commit strategy selected by the execution profile | "atomic commits", "one commit per phase", "single commit at the end" where commits are permitted |
| Run lint + typecheck + tests | "skip tests", "skip lint", "skip typecheck" |
| Implement all phases | "only phases 1 and 2", "skip phase 3" (phase positions are ordinal; labels like `A/B/C` map to `1/2/3`) |
| Abort tests on external dep missing | "stub missing services", "assume empty response for missing APIs" (stubs **ONLY in test code**, never in production modules) |
| Base branch = repository default branch | "base develop", "branch from release/2.0" |

For each recognized override, record before/after for the final report's "Overrides applied" section.

**Immutable core (cannot be overridden):** the final AC checklist and its traceability to the PRD, the Versioned-content rules, validation and final reporting. For direct invocations, the approval gates and PR workflow are also immutable. A complete harness profile may change only approvals, Git/GitHub steps and commit scheduling as defined above. Requests to squash, commit directly to the base branch or bypass human gates are always ignored and logged.

Ambiguous or contradictory instructions → default wins; logged under "Overrides ignored" with "ambiguous, kept default".

### Step 4: Pre-flight Checks

Run all applicable checks before writing code or mutating Git state. Any failure aborts before the first authorized mutation.

**4.1 Dependencies.** Locate the dependency content in the PRD semantically (typical headings: "Dependency Graph", "Dependencies"; typical shape: a table or list pairing each feature with its prerequisites). For each listed dependency of the target feature, verify it appears implemented on the base branch (look for the characteristic files described in that dependency's own `spec.md` Component Overview, or obvious source-level markers). A dependency that exists only in an open, unmerged PR counts as missing.

- Any dependency missing → abort. Report: "F<target> depends on F<N>, which is not implemented yet."
- If the PRD has no dependency content, skip this check.

**4.2 Attribution settings.** In a profile that creates commits or GitHub content, read the Claude Code settings that apply to this project: `~/.claude/settings.json`, `.claude/settings.json` and `.claude/settings.local.json`. Attribution must be off at every level that sets it:

- `includeCoAuthoredBy` must be `false` wherever it is present.
- `attribution.commit` and `attribution.pr` must be empty strings (`""`) wherever `attribution` is present.
- At least one of the two must be set to "off" at user or project level.

If any level enables attribution, or neither key is set anywhere → abort and tell the user which file and key to fix. Do not edit settings files yourself. The Text check still runs on every commit and PR regardless of this result.

**4.3 Local-only files.** In GitHub profiles, verify the repository is a git repo with a GitHub remote and that `gh auth status` succeeds. In local profiles, skip remote and authentication checks. When a Git repository exists, make sure `.git/info/exclude` contains entries covering `.harness/`, `.planning/`, `CLAUDE.md` and `.claude/`. Append any missing entry; this file is local and unversioned. Then run `git ls-files` on those paths: if any is already tracked, abort and tell the user.

**4.4 Base branch.** Resolve the base branch: the override if given, else `gh repo view --json defaultBranchRef`, else `main`.

### Step 5: Prepare the Branch (G1)

For local profiles, skip this entire step without changing Git state and continue to Step 6. For `autonomous + github`, the initial run authorization satisfies G1; record it and execute the remaining branch checks. Direct and `supervised + github` runs ask G1 normally.

**Resuming.** If `progress.md` names a branch that still exists locally or on the remote and its `Status` is not `merged`, this is a resumed run. Direct and supervised GitHub profiles ask G1 as "Posso retomar na branch `<branch>`?"; autonomous GitHub uses its recorded authorization. Check it out and go to Step 6. If `Status` is `PR open`, skip straight to Step 10 after checking the PR still exists.

**Fresh run.**

1. Derive the branch name from what the feature does (Versioned-content rule 5) and run the Text check on it. If a branch with that name already exists, pick a more specific name.
2. Apply G1 according to the selected profile.
3. `git fetch origin`, then create the branch from `origin/<base>`: `git switch -c <branch> origin/<base>`.
4. If the switch fails because of local changes, abort. Never stash, reset or discard the user's changes.
5. Create `progress.md` with the branch, base and the phases/units planned so far.

Uncommitted changes that do not block the switch are left untouched. They are never staged by this skill (explicit staging only).

### Step 6: Implementation Approval (G2)

Direct and `supervised + github` runs ask G2 normally. `Supervised + local` asks once before writing code. In autonomous profiles, the initial run authorization satisfies G2. Human gates always take precedence.

When G2 applies, state the branch or local target, the number of phases and the selected commit strategy. On "no", stop and report.

### Step 7: Execute Phases

For each phase of `plan.md`, in order:

**7.1 Skip if already done**

Check `progress.md`. A phase whose units are all checked, with every listed sha reachable from the current branch (`git merge-base --is-ancestor <sha> HEAD`), is skipped with status `already committed`. If some but not all units of a phase are checked (an interrupted run), resume the phase from its first unchecked unit. A checked unit whose sha is not on the branch is treated as unchecked and logged under `Deviations`.

**7.2 Implement**

Read spec.md sections relevant to the phase. Break the phase's steps into **implementation units**: the smallest self-contained changes that can be implemented and validated coherently (e.g. "add the `User` model", "add the migration for the `users` table", "add the `POST /users` route", "add tests for `POST /users`"). A single plan.md step is not automatically one unit; split it further if it touches unrelated concerns. Write the units into `progress.md` as unchecked items.

For each implementation unit, in order:

1. Implement it: write/edit only the files that unit needs.
2. Run the fast checks available (lint + typecheck) against the changed files. Non-zero exit means fix and retry under the same retry-limit policy as 7.3.
3. Mark the unit complete only after its fast checks pass.
4. Direct invocation: commit the unit immediately. Harness GitHub profile: add it to a semantic checkpoint. Harness local profile: do not stage or commit.

Sequence units so each checkpoint leaves the repo in as buildable a state as possible. When files genuinely cannot be split without an intermediate broken state, keep them together and record any material adaptation under `Deviations`.

**What counts as "done" for a phase** (all of the following, not just "I wrote the code"):

- Every file listed for this phase in spec.md's Component Overview exists and contains the described content.
- Every contract (API, schema, function signature) described for this phase matches what was written.
- Validation in 7.3 passes (hard fails resolved).
- If the phase produces runtime behavior that isn't covered by unit tests (UI pages, server routes, migrations, CLI commands), actually exercise it before claiming done: run the dev server / build / migration / command against a local environment and confirm it behaves. If the environment can't be brought up in this run, log the runtime check under `Soft-fails`. Do NOT silently claim the phase is done.

Writing code without running it is not "done". Declaring completion without meeting the checklist above is a violation of the skill's contract.

Adapt when reality diverges from the spec (column named `pinned` in DB vs `isPinned` in spec, different component file name, slightly different path, structurally compatible types). Specs are never 100% faithful to reality; adaptation is expected. Record every adaptation in a `Deviations` list for the final report. Do NOT abort on minor divergences.

**Abort the entire run only on:**

- Dependency feature missing (usually caught in Step 4; if discovered mid-phase, abort here).
- Hard fail past the retry limit in Step 7.3 below.

Missing external dependencies needed only by *tests* (e.g., `OPENAI_API_KEY` unavailable) do NOT abort the run; they soft-fail the affected test. The implementation code that calls the service is still written.

**7.3 Validate (phase gate)**

Once every implementation unit for the phase is implemented and handled according to the selected profile (7.2), run the full validation for the phase: discover commands at runtime (`package.json` `scripts`, or the non-Node equivalent: `Makefile`, `pyproject.toml`, `Cargo.toml`, `go.mod`, `vitest.config.*`, `jest.config.*`) and run lint + typecheck + tests.

- **Hard fail** = non-zero exit from lint, typecheck, or unit tests, where the failure is attributable to code this run changed. Retry up to the configured limit (default 3): read the error, fix it, record it according to the selected commit strategy, then re-run. After the limit, abort the whole run and go to Step 8. Existing commits are not reverted or squashed; the report marks the phase as not fully validated.
- **Soft fail** = validation cannot execute in this environment (e2e requiring browser/server not present; integration test requiring an external credential not set; suite explicitly marked non-runnable; command not found). Skip, log under `Soft-fails`, proceed.
- **Pre-existing failure** = validation fails but the failure is not attributable to code this run changed (touched unrelated files, existed on the base branch before this run). Log under `Pre-existing failures`, do NOT count against the retry budget, proceed.

Warnings without non-zero exit are never failures. The fast lint/typecheck pass in 7.2 step 2 catches most problems before they reach this gate; 7.3 exists to catch what only shows up once the whole phase is assembled: integration between units, the full test suite.

**7.4 Commit according to the selected profile**

**Direct invocation:** preserve the original atomic behavior. Each implementation unit gets its own commit immediately after fast checks pass.

**Harness GitHub profiles:** create compact semantic checkpoints, normally 1 to 3 commits for the feature and no more than 5 without a documented reason. A checkpoint may span several units or phases when they form one buildable concern. Include tests with the behavior they verify.

**Harness local profiles:** create no commit and perform no staging. Track completed units and validation results only in local `progress.md`.

For every commit-enabled profile:

1. Stage only the files for that checkpoint, one by one (`git add <file>`).
2. Run `git status` and confirm no local-only file is staged. If something is staged, unstage it and fix `.git/info/exclude`.
3. Write a Conventional Commit in pt-BR that describes the semantic result, then run the Text check.
4. Commit on the feature branch without skipping hooks.
5. Read the commit back with `git log -1 --format=%B` and confirm it still passes the Text check.
6. Associate all included implementation units with the short sha in `progress.md`.

If a hook rejects the commit, fix and retry under the same retry-limit policy as 7.3. Before the first push, a correction may be folded into the relevant semantic checkpoint when safe. Never rewrite a pushed commit. After push, land corrections as new fix commits.

Explicit commit overrides are honored only when the profile permits commits. `atomic commits` restores the original strategy. `one commit per phase` and `single commit at the end` remain available. `destination: local` always wins and creates no commits.

**7.5 Proceed**

Move to the next phase. A run-level abort (hard fail past retry limit, dependency missing mid-phase) stops execution and goes to Step 8 with whatever phases already committed.

### Step 8: Final Verification

After the last phase commits (or when the run aborted), run an independent verification pass over the whole feature before writing the report. This step exists because per-phase checks can miss regressions, and because AI commonly claims "done" when it isn't.

Perform all of the following; no step is optional:

**8.1 Full-suite validation**

Run the full validation suite on the entire repo (not just touched files): lint, typecheck, and the complete test suite as defined by the project. Do NOT filter to files this run changed.

- If failures appear that weren't flagged per-phase → they count as **regressions**. Attempt to fix up to the retry limit (same as hard-fail policy, each fix its own atomic commit). If still failing, do NOT declare success: status becomes `completed with regressions` and the failures are listed under `Regressions` in the report.
- Pre-existing failures already logged in Step 7.3 stay categorized as pre-existing; they do not become regressions.

**8.2 Component Overview walk-through**

Read spec.md's Component Overview (or equivalent file-list section) and, for every file listed, verify: the file exists, its described role is visible in the content, and its contracts (exports, routes, schemas) match the spec within the adaptation rules of Step 7.2.

Any missing file, missing export, or missing contract → add to `Missing from spec` in the report. Do NOT claim success if this list is non-empty.

**8.3 AC re-check**

For each acceptance criterion loaded in Step 2, locate the test(s) mapped to it via spec.md's Testing Strategy (or equivalent). Run those tests fresh right now (not just trusting that they passed in a prior phase). Mark the AC ✓ only if the test passes in this final re-check. If the test no longer passes → mark ✗, add to `Regressions`, and do not claim success.

ACs without mapped tests are marked ○ (no test).

**8.4 Environment smoke check (when applicable)**

If the feature produces runtime surfaces that per-phase validation couldn't exercise (UI page, HTTP endpoint, migration, CLI command), do one final exercise of each against a local environment (dev server, ephemeral DB, etc.). A quick load-and-interact is enough; the goal is to catch things unit tests don't.

If the environment cannot be brought up in this run, log each skipped smoke check under `Soft-fails`. Do NOT upgrade status to `success` unless every smoke check either passed or was honestly soft-failed.

**8.5 Versioned-content audit**

Run `git log origin/<base>..HEAD --format=%H%n%B` and apply the Text check to every commit message on the branch, plus the branch name. Also run `git diff --name-only origin/<base>...HEAD` and confirm none of the local-only files from Versioned-content rule 7 is in the diff. Any violation here (commits are not pushed yet) → report it in chat, explain the fix (e.g. reword a specific commit), and ask with AskUserQuestion before rewriting history. Never push a branch that fails this audit.

**8.6 Status decision**

The run's final status is determined by this step, not by whether phases committed:

- `success`: full suite green, every Component Overview item present, every AC's test passes in 8.3, every smoke check passed or soft-failed, audit 8.5 clean.
- `completed with regressions`: phases committed but 8.1 or 8.3 uncovered failures that the skill couldn't resolve.
- `incomplete`: `Missing from spec` (8.2) is non-empty.
- `aborted at phase <N>`: run stopped during Step 7 before reaching here.

Never report `success` when any of the checks above has an unresolved failure, even if every phase individually committed clean.

### Step 9: Final Report, then Open the PR (G3)

For local profiles, produce the complete report, set `Status: locally complete`, skip push and PR actions and stop after the report. For `autonomous + github`, the initial authorization satisfies G3 after Step 8 succeeds and no human gate is pending. Other GitHub runs ask G3 normally.

**9.1 Report.** Output the report to chat. Status comes from Step 8.6, never from "I think I finished". Chat may mention feature IDs; it may not use dashes.

```
Feature F<ID>: <name>

Status: success | completed with regressions | incomplete | aborted at phase <N>
Phases: <N> committed / <M> total
Branch: <branch> (base: <base>)
Commits: <K>

Acceptance Criteria (re-checked in Step 8.3):
✓ <AC text> (covered by <test name>)
✗ <AC text> (test failed after <K> retries: <error summary>)
○ <AC text> (no test covers this AC)

Cross-feature integration (if any):
✓ <criterion> (covered by <test name>)
...

Missing from spec (from Step 8.2):
* <file/export/contract that the spec required and is missing>

Regressions (from Step 8.1 or 8.3):
* <test name> started failing during this run: <error>

Deviations:
* <what was adapted and why>

Soft-fails:
* <what was skipped and why, including runtime smoke checks not exercised>

Pre-existing failures:
* <test name>: failed on entry to this run; left as-is

Overrides applied:
* Retry limit: 3 → unlimited

Overrides ignored:
* "<text>" (reason)

Abort reason (if status is aborted): <error>

Manual test checklist:
- [ ] <main flow step and expected result>
- [ ] <error case and expected result>
- [ ] <relevant edge case and expected result>
```

The manual test checklist always covers the main flow, error cases and relevant edge cases, written as concrete actions the user can perform with the expected result. It stays in chat only; it does not go into the PR.

If aborted, the report still lists whatever committed phases achieved and clearly marks which phase failed and why. If `completed with regressions` or `incomplete`, the report makes clear which checks failed so the user knows what to fix.

**9.2 Prepare the PR.** Skip this and stop if the status is `aborted at phase <N>` or audit 8.5 failed. Otherwise draft:

- **Title**: same format as commits, `tipo(escopo): descrição`, pt-BR, summarizing the whole change.
- **Body** in pt-BR, with exactly these sections:
  ```
  ## O que mudou
  <what the change does, as a short list of behaviors and components>

  ## Por que
  <the problem it solves or the need it addresses, in product terms>
  ```
  If the status is not `success`, add a `## Pendências` section listing what is known to be missing or failing, described by behavior (never by spec or AC ID).

Run the Text check on the title and the body.

**9.3 Apply G3.** Show the status, title and body. Direct and supervised GitHub profiles ask whether to push and open the PR. Autonomous GitHub proceeds under its recorded authorization only when status is `success` and no human gate is pending.

**9.4 Open it.** On approval: `git push -u origin <branch>`, then `gh pr create --base <base> --head <branch> --title "<title>" --body-file <temp file>` (write the body to a temp file outside the repo). Do not request reviewers or add labels unless the user asks. Record the PR URL in `progress.md` and set `Status: PR open`. Send the PR link in chat.

### Step 10: Review Loop and Merge (G4)

This step applies only to GitHub profiles. Direct and `supervised + github` runs keep the original G4 loop. An `autonomous + github` run uses the Autonomous GitHub review contract; initial authorization satisfies G4 only after review, checks and audits pass and no human gate is pending.

Right after the PR opens, direct and supervised GitHub profiles ask G4 with AskUserQuestion, e.g. "Revisou o PR #12 no GitHub? Posso fazer o merge?", offering "Aprovado, pode fazer o merge" and "Ainda não". The user can also answer in free text with requested changes. Autonomous GitHub instead runs the independent review loop defined above and uses its recorded authorization only after that loop passes.

GitHub does not let the author approve their own PR, so do not rely on `reviewDecision`. The user's explicit "yes" in chat is the approval.

- **"Ainda não"**: stop here. `progress.md` keeps `Status: PR open`, so a later invocation resumes at this step.
- **Changes requested** (in chat, by the autonomous reviewer or as review comments on GitHub, read with `gh pr view <n> --comments` and `gh api repos/{owner}/{repo}/pulls/<n>/comments`): apply each change under the selected commit strategy, re-run validation and push. Reply to GitHub comments only when authorized. Then repeat G4 for supervised profiles or repeat the independent review for autonomous GitHub.
- **Approved**: merge.

**Merge procedure:**

1. `gh pr view <n> --json state,mergeable,mergeStateStatus,statusCheckRollup`. The PR must be `OPEN` and `MERGEABLE`, with no failing required checks. If there are conflicts, supervised profiles ask before resolving; autonomous GitHub resolves only when no human gate covers the conflict, then pushes and repeats review. If checks are failing, report and stop.
2. `gh pr merge <n> --merge --delete-branch`. Always a merge commit: never squash or rebase, so the atomic commits stay in the base branch history. Keep GitHub's default merge-commit subject and body unless they fail the Text check; if they do, pass `--subject` and `--body` with compliant text.
3. `git switch <base>` and `git pull --ff-only origin <base>`. Delete the local feature branch if it still exists.
4. Set `Status: merged` in `progress.md`.
5. Confirm in chat: PR number, merge commit sha, branch deleted, local base updated.

In direct and supervised GitHub runs, never merge without a "yes" to G4 given after the PR opened. In an autonomous GitHub run, merge only under the complete preauthorization and review conditions above.

---

## RULES

**Always:**
- Require `spec.md` + `plan.md` in the target folder; abort without them.
- Locate AC and dependency content in the PRD semantically, never by fixed section number.
- Apply approval behavior from the selected profile. Direct invocation keeps G1 to G4 exactly; complete autonomous envelopes may preauthorize them, while human gates always stop the run.
- Create a dedicated branch from the up-to-date base branch before writing code.
- Follow every Versioned-content rule and run the Text check on every commit message, branch name, PR title, PR body and GitHub comment.
- Check the attribution settings in pre-flight (`includeCoAuthoredBy: false`, `attribution.commit` and `attribution.pr` empty).
- Use the selected commit strategy: original atomic commits for direct invocation, compact semantic checkpoints for harness GitHub profiles, and no commits for harness local profiles. Stage files explicitly whenever commits are enabled.
- Track progress in the local `progress.md`, never in commit messages.
- Adapt to minor spec/code divergences; log every adaptation under `Deviations`.
- Run validation after each phase; differentiate hard-fail (retry ≤ limit) from soft-fail (skip + log) from pre-existing failure (log, don't retry).
- Before claiming a phase is "done": confirm every file listed for that phase exists with the described content AND validation has passed. Writing code without running it is never "done".
- For phases that produce runtime surfaces (UI, HTTP route, migration, CLI), actually exercise them against a local environment before claiming done, or soft-fail the runtime check.
- Execute Step 8 (Final Verification) in full before reporting: full-suite re-run, Component Overview walk-through, AC re-check, environment smoke check, versioned-content audit.
- Derive the final status exclusively from Step 8.6. Report `success` only when every Step 8 check is green.
- End the report with the manual test checklist (chat only).
- Merge GitHub profiles with a merge commit (`--merge`). Never squash or rebase merge.

**Never:**
- Use an em dash (-) or en dash (-) anywhere, chat included.
- Mention feature/phase/requirement IDs (`F01`, `P2`, `RF02`, `US03`), the PRD, the spec or the plan in anything versioned or on GitHub.
- Add `Co-Authored-By` lines, "Generated with Claude Code", or any mention of Claude, Anthropic or AI to commits, PRs, comments or code.
- Commit `CLAUDE.md`, `.claude/`, the PRD, feature folders or `progress.md`, or add them to `.gitignore`, or mention them in versioned files.
- Commit directly to the base branch.
- Push, open the PR or merge without the approval or complete autonomous authorization required by the selected profile.
- Squash or rebase-merge the PR.
- Claim the run is `success` when Step 8 found regressions, missing-from-spec items, or unresolved failures, even if every phase individually committed clean.
- Skip the AC report or its traceability (immutable core).
- Skip Step 8 (Final Verification).
- Abort on name/path/type cosmetic divergences.
- Abort on external dependency missing for a test; soft-fail the test, keep implementing.
- Use `git add -A`, `git add .` or `git commit -a`.
- Skip git hooks.
- Stash, reset or discard the user's uncommitted changes.
- Edit Claude Code settings files; report misconfiguration and let the user fix it.
- Count pre-existing test failures against the retry budget.
- Re-run phases already fully committed on the branch (per `progress.md`).
- Insert service stubs in production modules; stubs are allowed only in test files.
- Explore the codebase upfront with a broad sweep; read files lazily as phases require.
- Declare a phase complete based only on "I wrote the files". The completion checklist in 7.2 must hold.

---

## Overrides

Free-form instructions at the end of the invocation override defaults. Examples:

- **Retry limit**: `no retry limit`, `max 5 tries`.
- **Autonomy**: `pause between phases`: asks with AskUserQuestion whether to continue after each phase.
- **Commit strategy**: direct invocation defaults to atomic; harness GitHub profiles default to compact semantic checkpoints. Override a commit-enabled profile with `atomic commits`, `one commit per phase` or `single commit at the end`. Harness local profiles always disable commits.
- **Validation**: `skip tests`, `skip lint`, `skip typecheck`.
- **Phase selection**: `only phases 1 and 2`, `skip phase 3` (phase positions are ordinal; labels `A/B/C` map to `1/2/3`).
- **External services**: `stub OpenAI`, `assume empty response for missing APIs` (stubs apply ONLY in test code; production modules keep the real call).
- **Base branch**: `base develop`, `branch from release/2.0`.

Unrecognized or contradictory overrides: default wins; logged under `Overrides ignored`.

**Immutable core**: the AC checklist and its traceability to the PRD, Versioned-content rules, validation and reporting cannot be overridden. Direct invocation also keeps approval gates and the PR workflow immutable. Only a complete harness profile can alter approvals, Git/GitHub steps and commit scheduling as documented above.

---

## Edge Cases

**No PRD found**: abort before starting.

**No spec.md or plan.md**: abort before starting.

**Dependency feature not implemented (or only in an unmerged PR)**: abort at Step 4 with a clear message.

**Ambiguous feature reference**: list candidates, abort asking which.

**Attribution enabled in some settings file**: abort at Step 4.2, naming the file and key to fix.

**Planning or AI files already tracked by git**: abort at Step 4.3 and tell the user which paths are tracked.

**No GitHub remote or `gh` not authenticated**: abort at Step 4.3 and tell the user what is missing.

**Working tree has unrelated changes at start**: proceed if the branch switch succeeds; those changes are never staged. If the switch fails because of them, abort without touching them.

**Already on a non-base branch at start**: ignore it; the new branch is always created from `origin/<base>`, unless `progress.md` says this is a resumed run on that branch.

**Phase or unit name contains special characters**: describe the unit in plain pt-BR words in the commit message (e.g. `feat(api): adiciona rota de upload`).

**Re-invocation after a partial run**: Step 5 detects the branch from `progress.md`, Step 7.1 skips fully covered phases and resumes a partially covered phase from its next unchecked unit. Uncommitted working-tree changes from a prior interrupted run stay as-is; the skill does not clean them up.

**Re-invocation after the PR was opened** (e.g. the user reviewed it in a later session): `progress.md` has `Status: PR open`; go straight to Step 10 and ask G4.

**PR closed without merge**: report it, set nothing in `progress.md` beyond noting it, and stop.

**Hard fail past the retry limit on a step that isn't part of any AC**: abort anyway; the skill cannot judge which failures are "acceptable". User can override with `skip tests` or similar.

**External tool emits warnings, not errors**: warnings are not failures. Only non-zero exit codes count.

**Override contradicts the core contract** (e.g., `simplify the spec, drop requirements`, `merge without asking`): ignore it, log under `Overrides ignored`, proceed with the full contract.

**Validation commands not discoverable**: if `package.json` / config files don't reveal lint/typecheck/test commands, log each missing command under `Soft-fails` and proceed.

**PRD has no AC content for this feature**: proceed with empty AC checklist and note under soft-fails.

**PRD has no dependency content**: skip Step 4.1 and proceed.

**Commit-message style is inconsistent in recent history**: use the exact format of Versioned-content rule 4.
