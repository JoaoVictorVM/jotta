# Publishing on GitHub

## Before the first push

1. Extract the clean release package.
2. Confirm that the hidden folders `.github`, `src/jotta/templates/.jotta` and `src/jotta/templates/.planning` are present.
3. Replace `<url-do-repositorio>` in the root README after the GitHub repository exists.
4. Review the MIT license choice and change it before publishing if another license is preferred.
5. Run the repository checks.

```bash
python scripts/repository_check.py
python scripts/self_test.py
jotta --root src/jotta/templates doctor
jotta --root src/jotta/templates models validate
```

Do not run the template `bootstrap.py` in the source repository. It is an installer step for consumer projects.

## First push

```bash
git init
git add .
git commit -m "feat(harness): publica versao inicial"
git branch -M main
git remote add origin <url-do-repositorio>
git push -u origin main
```

Inspect `git status` and `git diff --cached` before the commit. `.jotta/runtime`, Python caches, secrets, local planning and ZIP files must not appear.

## Suggested GitHub settings

- Enable GitHub Actions.
- Protect `main` after the initial push.
- Require the `validate` workflow before merge.
- Enable private vulnerability reporting under Security.
- Use merge commits if the repository should follow the harness convention.
- Add the topics `ai-agents`, `developer-tools`, `spec-driven-development`, `agent-harness` and `orca` when applicable.

Suggested description:

```text
Local-first open-source harness for spec-driven AI development, progressive context, quality gates, budget controls and Orca worktrees.
```

## Release

Create a GitHub release from the version in `src/jotta/templates/.jotta/VERSION` and summarize changes from `CHANGELOG.md`. Run `scripts/repository_check.py` again immediately before packaging or publishing a release.
