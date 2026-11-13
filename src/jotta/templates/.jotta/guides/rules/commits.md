# Commit rule

Format: `type(scope): description`.

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `style`, `perf`, `build`, `ci`, `chore`.

- Write the description in the language set by `commits.language` in `.jotta/config.yaml`, in lowercase, with a present-tense verb and no trailing period.
- Use 1 to 3 semantic commits per feature when possible.
- The normal limit is 5. Exceeding it requires a justification in the state.
- A commit is one logical, reviewable change, not one file or one function.
- Stage files explicitly. Do not use `git add .`, `git add -A` or `git commit -a`.
- Do not skip hooks.
- Do not add trailers or AI attribution.
