# Hooks

Rules written in Markdown depend on the agent choosing to follow them. Hooks move the most important rules into a check that runs before every tool call, so a forbidden action is stopped even when the agent ignores or forgets the rule.

## `jotta hook pre-tool-use`

The command reads one event in the Claude Code hook format from stdin and answers with an exit code:

| Exit code | Meaning |
|---|---|
| `0` | The tool call may run. Nothing is printed. |
| `2` | The tool call is blocked. The reason is printed on stderr and shown to the agent. |
| `1` | The event was not valid JSON. The hook reports an error without blocking. |

The guard finds the project from the event's `cwd`, walking up to the closest `.jotta/`, or from the global `--root` option. Outside a Jotta project it still blocks dangerous commands, using `cwd` as the project boundary, but it writes no log.

## Rules

Each rule matches an entry in the `deny` list of `.jotta/policy/permissions.md`.

| Rule | Blocks |
|---|---|
| `force-push` | `git push` with `--force`, `-f`, `--force-with-lease`, `--mirror` or `--delete`, and `+` or `:` refspecs |
| `hard-reset` | `git reset --hard` |
| `bypass-branch-protection` | `--no-verify` on `git commit` or `git push`, `gh pr merge --admin`, and `gh api` calls that change branch protection or rulesets |
| `read-secrets` | Reading or editing `.env` files, keys, certificates, credential files and anything under `.ssh`, `.aws` or `.gnupg`, through file tools, search tools or shell arguments. Example files such as `.env.example` are allowed, and so is creating a new file with `Write`. |
| `delete-outside-project` | Recursive `rm` of the project root, of anything outside it, or of a target that cannot be verified because it uses variables, globs or `~` |

Shell commands are split on `;`, `&&`, `||`, `|` and newlines, and environment assignments and wrappers such as `sudo` and `env` are skipped, so a forbidden command cannot hide behind another one.

The guard is conservative. It prefers blocking a command it cannot verify, and the agent then has to ask the user or find a narrower command. A blocked command that the user really wants can always be run by the user.

## Log

Every block is appended to `.jotta/runtime/logs/hooks.jsonl` with the time, session, tool, a truncated copy of the input, the rule and the reason. Allowed calls are not logged.

## Configuring Claude Code

Add the hook to the project's `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Read|Edit|MultiEdit|Write|NotebookEdit|Grep|Glob",
        "hooks": [{ "type": "command", "command": "jotta hook pre-tool-use" }]
      }
    ]
  }
}
```

The `jotta` command must be on the `PATH` of the shell that Claude Code starts.
