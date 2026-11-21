# Hooks

Rules written in Markdown depend on the agent choosing to follow them. Hooks move the most important rules into a check that runs before every tool call, so a forbidden action is stopped even when the agent ignores or forgets the rule.

## `jotta hook pre-tool-use`

The command reads one event in the Claude Code hook format from stdin and answers with an exit code:

| Exit code | Meaning |
|---|---|
| `0` | The tool call may run. Nothing is printed, unless the call raised a warning: then a `systemMessage` is printed on stdout for the user. |
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

| `widen-scope` | An agent running `jotta scope allow`, directly or through `python -m jotta` |

Shell commands are split on `;`, `&&`, `||`, `|` and newlines, and environment assignments and wrappers such as `sudo` and `env` are skipped, so a forbidden command cannot hide behind another one.

The guard is conservative. It prefers blocking a command it cannot verify, and the agent then has to ask the user or find a narrower command. A blocked command that the user really wants can always be run by the user.

## Task scope

`jotta prepare` records in the context packet the files the task may edit:

- the paths in the first column of the tables in the feature's `spec.md`, such as the component and test file tables;
- each path passed with `--allow`, which accepts files, directories (ending in `/`) and globs.

Files under `.planning/` are always allowed. For `Edit`, `MultiEdit`, `Write` and `NotebookEdit` calls during an active run, the hook compares the target with that list, in the project or in a worker's worktree:

| Profile | Edit outside the scope |
|---|---|
| `strict` | Blocked, rule `edit-outside-task-scope` |
| `lean` | Allowed with a warning, logged as `warn` |
| `manual-classic` | Not checked |

When the packet declares no paths, nothing is checked. Only a person widens the scope:

```bash
jotta scope allow src/payments.py --reason "shared helper changes signature"
jotta scope show
```

The command records each addition and its reason in the packet. The guard refuses it when an agent runs it. Edits made through shell commands, such as `sed -i`, are not covered by this check.

## `jotta hook post-tool-use`

After an `Edit`, `MultiEdit`, `Write` or `NotebookEdit` call changes a code file, the hook runs the quality profile set in the `post_edit` section of `.jotta/sensors/computational/gates.json`, which is `smoke` by default. Markdown and text files, and files under `.planning/`, `.jotta/` and `.git/`, do not trigger it.

```json
"post_edit": { "profile": "smoke", "debounce_seconds": 20 }
```

- **Debounce.** A burst of edits runs the profile once. An edit within `debounce_seconds` of the last run only marks the check as pending, and the next edit after the window runs it. After a failure the window is ignored, so each fix is checked at once.
- **Feedback.** When the profile passes, the hook prints nothing. When it fails, the hook exits with code 2 and prints the compact receipt on stderr: the failing command, its exit code, the relevant lines and the paths of the full log and the receipt. Claude Code shows that message to the agent right after the edit that caused it.
- **State.** The last run, its status, its receipt and whether a check is pending live in `.jotta/runtime/state/post-edit.json`.

An empty profile does nothing. `jotta install` fills `smoke` with the linter and type checker it detects; keep it fast, so the hook stays within the agent's hook timeout.

## `jotta hook stop`

The `Stop` hook runs when the agent tries to end its turn. While a task is active (a run in `preparing` or `running`, at the `prepared`, `implementing` or `validating` stage), the agent may stop only when the task has a valid quality receipt:

- the receipt comes from the profile the run's profile requires, or a stronger one (`smoke` < `feature` < `full`);
- its status is `passed`, or `skipped` because the profile has no commands;
- it was written after the task was prepared and after the last code edit recorded by the `PostToolUse` hook.

Otherwise the hook exits with code 2 and tells the agent which profile to run, or to record the task as blocked with `jotta checkpoint --status blocked --blocker <reason>`. The required profiles live in the `completion` section of `gates.json`:

```json
"completion": {
  "profiles": { "lean": "smoke", "strict": "feature", "manual-classic": "feature" },
  "max_consecutive_blocks": 3
}
```

A `null` profile disables the check for that run profile. To avoid an endless loop, after `max_consecutive_blocks` refusals in a row for the same task the agent may stop, but the run is marked `blocked` with the missing receipt as the blocker, so the task is never recorded as done without its gate.

## Log

Every block and every warning, including the `Stop` refusals, is appended to `.jotta/runtime/logs/hooks.jsonl` with the time, session, tool, a truncated copy of the input, the decision, the rule and the reason. Allowed calls are not logged.

## Configuring Claude Code

`jotta install` adds the hooks to the project's `.claude/settings.json`, and `jotta adapter claude` adds them to an existing installation. Both keep the settings and hooks already in the file. The resulting entries are:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash|Read|Edit|MultiEdit|Write|NotebookEdit|Grep|Glob",
        "hooks": [{ "type": "command", "command": "jotta hook pre-tool-use" }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|MultiEdit|Write|NotebookEdit",
        "hooks": [{ "type": "command", "command": "jotta hook post-tool-use" }]
      }
    ],
    "Stop": [{ "hooks": [{ "type": "command", "command": "jotta hook stop" }] }]
  }
}
```

The `jotta` command must be on the `PATH` of the shell that Claude Code starts. `jotta doctor` warns when one of the hooks is missing. See [Claude Code adapter](./claude-code.md) for the subagents and skills generated next to them, and [Codex adapter](./codex.md) for the same hooks in Codex, enabled with `--agent codex`.
