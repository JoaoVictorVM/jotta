<a id="readme-top"></a>

<br />
<div align="center">
  <a href="https://github.com/JoaoVictorVM/jotta">
    <img src="./assets/jotta-icon.png" alt="jotta logo" width="160">
  </a>

  <h1 align="center">jotta</h1>

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

## What jotta Is

AI coding work needs requirements, a bounded task, the right context and evidence that the result works.

**jotta connects those steps inside your project.** It provides agent instructions, skills and a Python runtime to move from a PRD to feature specs, implementation, quality checks and delivery. Recoverable state keeps track of the work between sessions.

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

High-risk work in `lean` is elevated to `strict` during preparation. See the [runtime guide](./.harness/README.md) for the lifecycle and internal commands.

## Requirements

| Tool | When it is needed |
|---|---|
| Python 3.10+ | Installation and harness scripts. |
| Compatible coding agent | An agent that reads `AGENTS.md` or `CLAUDE.md`. |
| Git | GitHub workflows. |
| Orca CLI | Managed worktrees and visible agent sessions. |

Local use works without Git or Orca. Autonomous GitHub execution blocks when Orca is unavailable.

<a id="install"></a>

## Install

Clone this repository and point the installer at the project where you want to use the harness:

```bash
git clone https://github.com/JoaoVictorVM/jotta.git
python jotta/scripts/install.py --target /path/to/project
```

On Windows:

```powershell
python jotta\scripts\install.py --target C:\path\to\project
```

The installer checks for conflicts before writing, refuses to overwrite existing files and runs the local bootstrap by default. Use `--no-bootstrap` to perform that step manually.

<details>
<summary>Manual installation</summary>

Copy `.harness/`, `.planning/`, `AGENTS.md` and `CLAUDE.md` into the consumer project. Then run from that project's root:

```bash
python .harness/scripts/bootstrap.py
python .harness/scripts/harness.py doctor
```

</details>

> [!IMPORTANT]
> Run bootstrap in the consumer project. It adds local harness files to that project's `.git/info/exclude` and should not run inside the jotta source repository.

<a id="getting-started"></a>

## Getting Started

1. Write your product requirements in `.planning/PRD.md` using `prd-writer`.
2. Set your project's real validation commands in `.harness/sensors/computational/gates.json`.
3. Run `python .harness/scripts/harness.py doctor` from the consumer project.
4. Choose a prompt from `.harness/prompts/` or ask your agent in natural language.

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
.harness/                    Runtime, skills, workflows and configuration
.planning/                   Local templates for PRDs, specs and plans
scripts/install.py           Installer for consumer projects
scripts/repository_check.py  Public repository and package checks
docs/                        Publishing guide and project assets
AGENTS.md                    Entry point for coding agents
CLAUDE.md                    Bridge to AGENTS.md
```

## Development

Run the repository checks from the jotta source checkout:

```bash
python scripts/repository_check.py
python .harness/scripts/self_test.py
python .harness/scripts/harness.py doctor
python .harness/scripts/model_router.py validate
```

CI runs these checks on pushes and pull requests. See the [publishing guide](./docs/PUBLISHING.md) for repository setup and GitHub configuration.

## Security and Local Data

Keep consumer-project runtime files, real planning documents, credentials, logs and execution state out of the public repository. The source repository's `.gitignore` covers generated development artifacts.

Read [SECURITY.md](./SECURITY.md) to report a vulnerability.

<a id="contributing"></a>

## Contributing

Read [CONTRIBUTING.md](./CONTRIBUTING.md) for the development workflow. You can help with bug reports, documentation and improvements to the harness. Behavior changes should include or update a case in `.harness/evals/cases/`.

## License

Distributed under the **MIT License**. See [LICENSE](./LICENSE).

<p align="right"><a href="#readme-top">Back to top</a></p>
