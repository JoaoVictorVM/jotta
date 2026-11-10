<a id="readme-top"></a>

<br />
<div align="center">
  <a href="https://github.com/JoaoVictorVM/jotta">
    <img src="./assets/jotta-icon.png" alt="Jotta logo" width="160">
  </a>

  <h1 align="center">Jotta</h1>

  <p align="center">
    <b>A structured workflow for AI-assisted development.</b>
    <br />
    From PRD to verified delivery, with progressive context, local state and budget controls.
    <br />
    <a href="./README.pt-BR.md">Português (Brasil)</a>
  </p>

  <p align="center">
    <a href="https://github.com/JoaoVictorVM/jotta/actions/workflows/validate.yml"><img alt="CI" src="https://img.shields.io/github/actions/workflow/status/JoaoVictorVM/jotta/validate.yml?branch=main&amp;label=ci&amp;style=flat-square"></a>
    <a href="./LICENSE"><img alt="MIT" src="https://img.shields.io/badge/license-MIT-blue?style=flat-square"></a>
    <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-3776AB?style=flat-square">
    <a href="https://github.com/JoaoVictorVM/jotta/stargazers"><img alt="Stars" src="https://img.shields.io/github/stars/JoaoVictorVM/jotta?style=flat-square"></a>
  </p>

  <p align="center">
    <a href="#install">Install</a>
    · <a href="#getting-started">Getting started</a>
    · <a href="https://github.com/JoaoVictorVM/jotta/issues">Bugs &amp; ideas</a>
    · <a href="./SECURITY.md">Security</a>
    · <a href="#contributing">Contributing</a>
  </p>
</div>

## What Jotta Is

AI coding work needs requirements, a bounded task, the right context and evidence that the result works.

**Jotta connects those steps inside your project.** It provides agent instructions, skills and a Python runtime to move from a PRD to feature specs, implementation, quality checks and delivery. Recoverable state keeps track of the work between sessions.

Planning documents and execution state stay local to the consumer project. Agents still use their configured model providers, and GitHub delivery uses GitHub and Orca.

## What It Does

**Give each task the context it needs**

- Route product, change and validation requests through focused workflows.
- Load compact task packets instead of the entire project history.
- Keep PRDs, specs, plans and memory in the consumer project.

**Make execution recoverable**

- Record tasks, checkpoints and execution status in local JSON files.
- Preserve blocked or unverifiable worktrees for inspection and recovery.
- Use Orca-managed worktrees for autonomous GitHub delivery.

**Control validation and cost**

- Configure smoke, feature and full quality checks for your project.
- Apply budget gates that can stop execution at configured limits.
- Route tasks to OpenAI, Anthropic or the model inherited from the platform.

## Execution Profiles

| Profile | Workflow |
|---|---|
| `manual-classic` | Detailed interviews and human gates G1 to G4. |
| `lean` | Progressive context, smoke checks per feature and final review. The autonomous default. |
| `strict` | Deeper validation and review for each feature. |

High-risk work in `lean` is elevated to `strict` during preparation. See the [runtime guide](./src/jotta/templates/.jotta/README.md) for the lifecycle and internal commands.

## Requirements

| Tool | When it is needed |
|---|---|
| Python 3.10+ | The `jotta` package and command. |
| Compatible coding agent | An agent that reads `AGENTS.md` or `CLAUDE.md`. |
| Git | GitHub workflows. |
| Orca CLI | Managed worktrees and visible agent sessions. |

Local use works without Git or Orca. Autonomous GitHub execution blocks when Orca is unavailable.

<a id="install"></a>

## Install

Install the package, then install the harness into the project where you want to use it:

```bash
python -m pip install git+https://github.com/JoaoVictorVM/jotta.git
cd /path/to/project
jotta install
jotta doctor
```

The workflows and skills copied into the project call the `jotta` command, so install the package in the Python environment you use in that project.

`jotta install` copies `.jotta/`, `.planning/`, `AGENTS.md` and `CLAUDE.md`, creates the local planning and runtime folders and adds the harness files to the project's `.git/info/exclude`, so they stay out of commits. It never overwrites a file silently.

| Option | Effect |
|---|---|
| `--target <dir>` | Install into another directory instead of the current one. |
| `--dry-run` | Show the files, folders and Git exclusions without writing anything. |
| `--force-overwrite` | Replace existing harness files after confirmation. Add `--yes` to skip the question. |
| `--no-git-exclude` | Keep `.git/info/exclude` untouched, for projects that version the harness. |

<a id="getting-started"></a>

## Getting Started

1. Write your product requirements in `.planning/PRD.md` using `prd-writer`.
2. Set your project's real validation commands in `.jotta/sensors/computational/gates.json`.
3. Run `jotta doctor` from the consumer project.
4. Choose a prompt from `.jotta/prompts/` or ask your agent in natural language.

For example:

```text
Implement the product described in .planning/PRD.md using the lean profile,
autonomously, with delivery on GitHub.
```

You can also ask for smaller tasks:

```text
Classify and implement this bug locally.
Implement F03 using manual-classic.
Resume the recorded run.
Show harness status.
```

## Project Structure

```text
src/jotta/                   Python package and the jotta command
src/jotta/templates/         Files installed into a project: .jotta/, .planning/, AGENTS.md and CLAUDE.md
tests/                       Package tests
scripts/repository_check.py  Public repository and package checks
scripts/self_test.py         Template regression checks
docs/                        Publishing guide and project assets
AGENTS.md                    Instructions for agents developing Jotta
CLAUDE.md                    Bridge to AGENTS.md
```

## Development

Install the package in editable mode with the development tools:

```bash
python -m pip install -e ".[dev]"
jotta --help
python -m pytest
```

Run the repository checks from the Jotta source checkout:

```bash
python scripts/repository_check.py
python scripts/self_test.py
jotta --root src/jotta/templates doctor
jotta --root src/jotta/templates models validate
```

CI runs these checks on pushes and pull requests. See the [publishing guide](./docs/PUBLISHING.md) for repository setup and GitHub configuration.

## Security and Local Data

Keep consumer-project runtime files, real planning documents, credentials, logs and execution state out of the public repository. The source repository's `.gitignore` covers generated development artifacts.

Read [SECURITY.md](./SECURITY.md) to report a vulnerability.

<a id="contributing"></a>

## Contributing

Read [CONTRIBUTING.md](./CONTRIBUTING.md) for the development workflow. You can help with bug reports, documentation and improvements to the harness. Behavior changes should include or update a case in `src/jotta/templates/.jotta/evals/cases/`.

## License

Distributed under the **MIT License**. See [LICENSE](./LICENSE).

<p align="right"><a href="#readme-top">Back to top</a></p>
