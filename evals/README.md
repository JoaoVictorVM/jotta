# Evals

These evals measure how an agent performs real tasks with Jotta installed: whether the result works, what it cost and which gates fired. They complement the behavior cases in `src/jotta/templates/.jotta/evals/`, which are scripts a person follows to check one harness decision at a time.

| Path | Contents |
|---|---|
| `fixtures/` | Small apps the tasks run on. |
| `cases/` | One file per task: the request, the workflow, the expected risk and the behavior the result must show. |

## The tasks-api fixture

`fixtures/tasks-api` is a JSON task API written with the Python standard library and tested with pytest. Its `PRD.md` describes five features. The cases cover:

| Case | Kind | Workflow | Risk |
|---|---|---|---|
| `tasks-api-f01-status-filter` | Feature | Product, F01 | Normal |
| `tasks-api-f02-due-dates` | Feature | Product, F02 | Normal |
| `tasks-api-f03-tags` | Feature | Product, F03 after F01 | Normal |
| `tasks-api-f04-token-auth` | Feature | Product, F04 | High, with a human gate |
| `tasks-api-f05-stats` | Feature | Product, F05 after F02 | Normal |
| `tasks-api-bug-pagination-offset` | Bug | Change | Normal |
| `tasks-api-refactor-task-validation` | Refactor | Change | Normal |

The fixture ships with the bug of the pagination case, and the code that the refactor case removes is duplicated on purpose. Do not fix either one in the fixture.

## Running a task by hand

1. Copy the fixture to an empty folder outside this repository, make it a Git repository and install Jotta:

   ```bash
   cp -r evals/fixtures/tasks-api /tmp/tasks-api && cd /tmp/tasks-api
   git init -q && git add . && git commit -qm "chore: fixture inicial"
   jotta install
   cp PRD.md .planning/PRD.md
   jotta validate-prd && jotta sync-tasks
   ```

2. Start the agent in that folder and send it the case's `prompt`.
3. Compare the result with the case's `expected` list.

A product case runs on its PRD feature: `jotta prepare F01`. A change case runs on its change slug: `jotta prepare fix-pagination-offset --scope change`. A case with `depends_on` needs those cases done first, as the PRD dependencies require.

## Case format

Cases use a small subset of YAML that `jotta.evals.cases` reads without dependencies: `key: value`, `key: |` text blocks and `key:` lists of `- item` strings.

| Key | Meaning |
|---|---|
| `id` | The file name without `.yaml` |
| `title` | A short name |
| `fixture` | A folder under `fixtures/` |
| `kind` | `feature`, `bug` or `refactor` |
| `workflow` | `product` for a PRD feature, `change` for a bug or a refactor |
| `task` | The PRD feature, such as `F01`, or the change slug |
| `risk` | The risk the harness must find: `normal` or `high` |
| `human_gate` | `true` when the run must stop for a person; required for `high` |
| `depends_on` | Cases that must be done first |
| `prompt` | What the user asks the agent |
| `expected` | The behavior the result must show |

`tests/test_eval_fixture.py` checks that every case is valid, that the product cases match the fixture's PRD and the risk that `jotta prepare` assigns, that the fixture's tests pass and its bug reproduces, and that the tasks can be prepared with Jotta installed.
