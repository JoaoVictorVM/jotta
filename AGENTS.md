# AGENTS.md

Instructions for agents working on the Jotta source repository. The harness that Jotta installs into other projects lives in `src/jotta/templates/`; its own `AGENTS.md` is the entry point for agents in those projects.

## Layout

| Path | Contents |
|---|---|
| `src/jotta/` | Python package and the `jotta` command |
| `src/jotta/templates/` | Files copied into a project: `AGENTS.md`, `CLAUDE.md`, `.jotta/` and `.planning/` |
| `tests/` | pytest suite: `tests/unit/` for modules, the top level for commands and installation |
| `scripts/` | Repository tooling: public repository and package check |
| `docs/` | Human documentation |

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
ruff check src tests
ruff format --check src tests
mypy
python scripts/repository_check.py
jotta --root src/jotta/templates doctor
```

## Rules

- Keep the runtime free of third-party dependencies.
- Behavior changes to the runtime need tests. Changes to agent behavior should add or update a case in `src/jotta/templates/.jotta/evals/cases/`.
- Template files are product content: changing them changes what every installed project receives.
- Never use the characters U+2013 or U+2014 in versioned files. In code, write them as Unicode escape sequences.
- Commits follow Conventional Commits with a lowercase pt-BR description and no AI attribution. Stage files explicitly.
- Branches use `type/short-description`. Pull requests are merged with a merge commit after green CI.
