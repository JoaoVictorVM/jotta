"""Generate the Claude Code configuration of a project from its harness files.

The adapter writes these files under ``.claude/``:

- ``settings.json`` gets the ``jotta hook`` commands and the ``Bash`` permission rules of the active execution
  profile, merged into any existing settings without removing or duplicating the user's entries;
- ``jotta-permissions.json`` records the permission rules the adapter added, so a profile change replaces them;
- ``agents/<name>.md`` gets one subagent per role in ``.jotta/agents/``, with read-only tools for the reviewers;
- ``skills/<name>/SKILL.md`` gets one entry per skill in ``.jotta/skills/``, pointing back to the canonical file so
  its references keep resolving and there is only one copy to maintain.
"""

from __future__ import annotations

import json
from pathlib import Path

from jotta.adapters.common import (
    AdapterPlan,
    HookSpec,
    SettingsError,
    apply_adapter,
    first_paragraph,
    frontmatter,
    is_generated,
    marker,
    merge_hooks,
    missing_hook_events,
    render_json,
    split_frontmatter,
    stage,
    stage_hooks,
    stage_skills,
)
from jotta.adapters.permissions import EFFECTS, ShellRules, shell_rules
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict

Rules = dict[str, list[str]]

__all__ = ["apply_adapter", "first_paragraph", "merge_settings", "missing_hooks", "plan_adapter", "split_frontmatter"]

HOOKS: HookSpec = {
    "PreToolUse": {
        "matcher": "Bash|Read|Edit|MultiEdit|Write|NotebookEdit|Grep|Glob",
        "command": "jotta hook pre-tool-use",
    },
    "PostToolUse": {"matcher": "Edit|MultiEdit|Write|NotebookEdit", "command": "jotta hook post-tool-use"},
    "Stop": {"matcher": None, "command": "jotta hook stop"},
}
READ_ONLY_TOOLS = "Read, Grep, Glob"
AGENT_TOOLS = {
    "reviewer": READ_ONLY_TOOLS,
    "qa-reviewer": READ_ONLY_TOOLS,
    "spec-author": "Read, Grep, Glob, Write, Edit",
}


def claude_dir(paths: ProjectPaths) -> Path:
    return paths.root / ".claude"


def merge_settings(current: JSONDict) -> JSONDict:
    """Add the Jotta hooks to ``current`` settings, keeping every existing key and hook."""
    return merge_hooks(current, HOOKS)


def agent_file(source: Path, paths: ProjectPaths) -> str:
    """A Claude Code subagent built from a harness role."""
    name = source.stem
    body = source.read_text(encoding="utf-8")
    header = frontmatter({"name": name, "description": first_paragraph(body), "tools": AGENT_TOOLS.get(name, "")})
    return f"{header}\n\n<!-- {marker(paths.relative(source), 'claude')} -->\n\n{body}"


def claude_rules(shell: ShellRules) -> Rules:
    return {effect: [f"Bash({pattern})" for pattern in patterns] for effect, patterns in shell.by_effect().items()}


def read_record(path: Path) -> Rules:
    """The permission rules a previous run added, or none when the record is missing or unreadable."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(data, dict):
        return {}
    return {effect: [str(item) for item in data.get(effect) or [] if isinstance(item, str)] for effect in EFFECTS}


def merge_permissions(current: JSONDict, previous: Rules, rules: Rules) -> JSONDict:
    """Replace the rules a previous run added with ``rules``, keeping every rule of the user."""
    permissions = current.get("permissions", {})
    if not isinstance(permissions, dict):
        raise SettingsError("`permissions` is not an object")
    permissions = dict(permissions)
    for effect in EFFECTS:
        existing = permissions.get(effect, [])
        if not isinstance(existing, list):
            raise SettingsError(f"`permissions.{effect}` is not a list")
        kept = [item for item in existing if item not in previous.get(effect, [])]
        merged = kept + [item for item in rules[effect] if item not in kept]
        if merged:
            permissions[effect] = merged
        else:
            permissions.pop(effect, None)
    result = dict(current)
    if permissions:
        result["permissions"] = permissions
    else:
        result.pop("permissions", None)
    return result


def record_file(paths: ProjectPaths, shell: ShellRules, rules: Rules) -> str:
    origin = paths.relative(paths.policy / "profile-permissions.json")
    return render_json({"generated": marker(origin, "claude"), "profile": shell.profile, **rules})


def plan_adapter(paths: ProjectPaths, profile: str | None = None) -> AdapterPlan:
    """Compute the Claude Code configuration of a project without touching the disk."""
    plan = AdapterPlan(root=paths.root)
    target = claude_dir(paths)
    try:
        shell = shell_rules(paths, profile)
    except (OSError, ValueError) as exc:
        plan.error = f"cannot read the profile permissions: {exc}"
        return plan
    record = target / "jotta-permissions.json"
    rules = claude_rules(shell)
    previous = read_record(record) if is_generated(record) else {}
    stage_hooks(
        plan,
        target / "settings.json",
        HOOKS,
        paths,
        extra=lambda settings: merge_permissions(settings, previous, rules),
    )
    if plan.error:
        return plan
    stage(plan, record, record_file(paths, shell, rules))
    for source in sorted((paths.harness / "agents").glob("*.md")):
        stage(plan, target / "agents" / source.name, agent_file(source, paths))
    stage_skills(plan, paths, target / "skills", "claude")
    return plan


def missing_hooks(paths: ProjectPaths) -> list[str]:
    """The Jotta hook events missing from the project's Claude Code settings."""
    return missing_hook_events(claude_dir(paths) / "settings.json", HOOKS)
