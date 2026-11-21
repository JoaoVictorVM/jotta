"""Generate the OpenCode configuration of a project from its harness files.

OpenCode reads ``AGENTS.md`` on its own, so the adapter adds what it cannot infer:

- ``.opencode/opencode.jsonc`` with the shell rules of the active profile, from
  ``.jotta/policy/profile-permissions.json``, and rules that mirror the ``deny`` list of
  ``.jotta/policy/permissions.md``, unless the project keeps its own ``.opencode/opencode.json``;
- ``.opencode/agents/<name>.md`` with one subagent per role in ``.jotta/agents/``, read-only for the reviewers;
- ``.opencode/skills/<name>/SKILL.md`` with one entry per skill in ``.jotta/skills/``, pointing to the canonical file.

OpenCode evaluates permission rules in order and the last matching rule wins. The shell rules of the active profile
come first, from the broad ``ask`` to the narrow ``deny``; the secret rules follow, with the exceptions for example
files right after the patterns they relax; the fixed denials of the policy come last, so no profile relaxes them.
OpenCode has no command hooks, so the smoke check after an edit and the receipt before stopping are not enforced;
``docs/concepts/opencode.md`` lists the differences.
"""

from __future__ import annotations

import json
from pathlib import Path

from jotta.adapters.common import AdapterPlan, first_paragraph, is_generated, marker, stage, stage_skills
from jotta.adapters.permissions import ShellRules, shell_rules
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict
from jotta.hooks.guard import SAFE_SEGMENTS, SECRET_DIRECTORIES, SECRET_PATTERNS

SCHEMA = "https://opencode.ai/config.json"
CONFIG_NAME = "opencode.jsonc"
FILE_ACTIONS = ("read", "edit")
SHELL_DENY = (
    # force-push
    "git push -f*",
    "git push * -f*",
    "git push *--force*",
    "git push *--mirror*",
    "git push *--delete*",
    "git push * +*",
    "git push * :*",
    # hard-reset
    "git reset *--hard*",
    # bypass-branch-protection
    "git push *--no-verify*",
    "git commit *--no-verify*",
    "gh pr merge *--admin*",
    # widen-scope
    "jotta scope allow*",
    "jotta * scope allow*",
    "* -m jotta scope allow*",
)
READ_ONLY_ROLES = {"reviewer", "qa-reviewer"}
NO_SHELL_ROLES = READ_ONLY_ROLES | {"spec-author"}


def opencode_dir(paths: ProjectPaths) -> Path:
    return paths.root / ".opencode"


def rule(action: str, resource: str, effect: str) -> JSONDict:
    return {"action": action, "resource": resource, "effect": effect}


def anywhere(pattern: str) -> list[str]:
    """A path pattern matched both as given and below any directory."""
    return [pattern, f"*/{pattern}"]


def secret_rules() -> list[JSONDict]:
    """Deny reading or editing credential files, in the order the hook guard decides them."""
    denied = [pattern for name in SECRET_PATTERNS for pattern in anywhere(name)]
    safe = [f"*.{segment}" for segment in sorted(SAFE_SEGMENTS)] + ["*.pub"]
    directories = [pattern for name in SECRET_DIRECTORIES for pattern in anywhere(f"{name}/*")]
    return [
        *(rule(action, pattern, "deny") for action in FILE_ACTIONS for pattern in denied),
        *(rule(action, pattern, "allow") for action in FILE_ACTIONS for pattern in safe),
        *(rule(action, pattern, "deny") for action in FILE_ACTIONS for pattern in directories),
    ]


def profile_rules(shell: ShellRules) -> list[JSONDict]:
    """The rules of the active profile: ask by default, then allow, ask and deny, so the most restrictive wins."""
    return [
        rule("shell", "*", "ask"),
        *(rule("shell", pattern, effect) for effect, patterns in shell.by_effect().items() for pattern in patterns),
    ]


def permission_rules(shell: ShellRules) -> list[JSONDict]:
    return [
        *profile_rules(shell),
        *secret_rules(),
        *(rule("shell", pattern, "deny") for pattern in SHELL_DENY),
        rule("external_directory", "*", "ask"),
    ]


def config_file(paths: ProjectPaths, shell: ShellRules) -> str:
    origin = paths.relative(paths.policy / "profile-permissions.json")
    body = json.dumps({"$schema": SCHEMA, "permissions": permission_rules(shell)}, indent=2)
    return f"// {marker(origin, 'opencode')}\n// profile: {shell.profile}\n{body}\n"


def agent_rules(name: str) -> list[JSONDict]:
    rules = [rule("edit", "*", "deny")] if name in READ_ONLY_ROLES else []
    return rules + ([rule("shell", "*", "deny")] if name in NO_SHELL_ROLES else [])


def agent_file(source: Path, paths: ProjectPaths) -> str:
    """An OpenCode subagent built from a harness role; its Markdown body is the system prompt."""
    name = source.stem
    body = source.read_text(encoding="utf-8")
    lines = ["---", f"description: {json.dumps(first_paragraph(body), ensure_ascii=False)}", "mode: subagent"]
    rules = agent_rules(name)
    if rules:
        lines.append("permissions:")
        for item in rules:
            lines += [
                f"  - action: {item['action']}",
                f'    resource: "{item["resource"]}"',
                f"    effect: {item['effect']}",
            ]
    lines += ["---", "", f"<!-- {marker(paths.relative(source), 'opencode')} -->", "", body]
    return "\n".join(lines)


def plan_adapter(paths: ProjectPaths, profile: str | None = None) -> AdapterPlan:
    """Compute the OpenCode configuration of a project without touching the disk."""
    plan = AdapterPlan(root=paths.root)
    target = opencode_dir(paths)
    try:
        shell = shell_rules(paths, profile)
    except (OSError, ValueError) as exc:
        plan.error = f"cannot read the profile permissions: {exc}"
        return plan
    if (target / "opencode.json").exists():
        plan.skipped.append(target / CONFIG_NAME)
    else:
        stage(plan, target / CONFIG_NAME, config_file(paths, shell))
    for source in sorted((paths.harness / "agents").glob("*.md")):
        stage(plan, target / "agents" / source.name, agent_file(source, paths))
    stage_skills(plan, paths, target / "skills", "opencode")
    return plan


def missing_config(paths: ProjectPaths) -> bool:
    """Whether a project that uses OpenCode lacks the generated permission rules."""
    target = opencode_dir(paths)
    return target.is_dir() and not is_generated(target / CONFIG_NAME)
