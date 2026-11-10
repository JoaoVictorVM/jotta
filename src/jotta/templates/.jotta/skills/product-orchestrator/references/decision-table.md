# Decision table

| Condition | Decision |
|---|---|
| User explicitly chooses a profile | Use that profile |
| No profile is given | Use `lean` |
| Lean task touches security, payments, destructive migrations or personal data | Elevate to `strict` and report it |
| User explicitly requests GitHub delivery | Use `github` destination |
| User explicitly requests local-only work | Use `local` destination and do not mutate Git |
| Autonomous GitHub work | Require an Orca worktree and visible worker terminal |
| Manual or supervised feature | Worktree is optional and follows the user request |
| Independent writers are proven safe | One worktree per writer |
| Shared foundation or central files | Execute sequentially |
| Bug or small change with clear behavior | Use `change`, no full PRD or feature spec |
| New product capability | Update PRD, then use `product` |
| Lean feature completes | Smoke validate, checkpoint, then advance |
| Product completes | Run `final-qa`, open one PR, review and merge with merge commit |
| Major product direction changes | Human gate |
