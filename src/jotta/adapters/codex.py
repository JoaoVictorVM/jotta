"""Generate the Codex configuration of a project from its harness files.

The adapter writes:

- ``.codex/hooks.json`` with the ``jotta hook --agent codex`` commands, merged into any existing hooks;
- ``.codex/config.toml`` with the approval and sandbox rules, only when the file is absent or was generated;
- ``.codex/agents/<name>.toml`` with one custom agent per role in ``.jotta/agents/``;
- ``.agents/skills/<name>/SKILL.md`` with one entry per skill in ``.jotta/skills/``, pointing to the canonical file.

Codex loads ``.codex/`` only in a trusted project, and runs a project hook only after the user reviews it with
``/hooks``. Codex custom agents have no tool list, so a read-only role is enforced by its instructions and by the
parent session's sandbox, not by a separate permission.
"""

from __future__ import annotations

import json
from pathlib import Path

from jotta.adapters.common import (
    AdapterPlan,
    HookSpec,
    first_paragraph,
    marker,
    missing_hook_events,
    stage,
    stage_hooks,
    stage_skills,
)
from jotta.core.paths import ProjectPaths

HOOKS: HookSpec = {
    "PreToolUse": {"matcher": "Bash|apply_patch", "command": "jotta hook pre-tool-use --agent codex"},
    "PostToolUse": {"matcher": "apply_patch", "command": "jotta hook post-tool-use --agent codex"},
    "Stop": {"matcher": None, "command": "jotta hook stop --agent codex"},
}
READ_ONLY_ROLES = {"reviewer", "qa-reviewer"}
READ_ONLY_RULE = (
    "You are read-only. Never edit, create or delete files, and never run commands that change the project, "
    "its Git state or anything outside it. Report findings instead."
)
CONFIG = """approval_policy = "on-request"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = false
"""


def codex_dir(paths: ProjectPaths) -> Path:
    return paths.root / ".codex"


def toml_string(value: str) -> str:
    """A TOML basic string. JSON string escapes are a subset of TOML's, so ``json.dumps`` produces a valid one."""
    return json.dumps(value, ensure_ascii=False)


def agent_file(source: Path, paths: ProjectPaths) -> str:
    """A Codex custom agent built from a harness role."""
    name = source.stem
    body = source.read_text(encoding="utf-8")
    instructions = f"{READ_ONLY_RULE}\n\n{body}" if name in READ_ONLY_ROLES else body
    return "\n".join(
        [
            f"# {marker(paths.relative(source), 'codex')}",
            f"name = {toml_string(name)}",
            f"description = {toml_string(first_paragraph(body))}",
            f"developer_instructions = {toml_string(instructions)}",
            "",
        ]
    )


def config_file(paths: ProjectPaths) -> str:
    return f"# {marker(paths.relative(paths.harness / 'policy' / 'permissions.md'), 'codex')}\n{CONFIG}"


def plan_adapter(paths: ProjectPaths) -> AdapterPlan:
    """Compute the Codex configuration of a project without touching the disk."""
    plan = AdapterPlan(root=paths.root)
    target = codex_dir(paths)
    stage_hooks(plan, target / "hooks.json", HOOKS, paths)
    stage(plan, target / "config.toml", config_file(paths))
    for source in sorted((paths.harness / "agents").glob("*.md")):
        stage(plan, target / "agents" / f"{source.stem}.toml", agent_file(source, paths))
    stage_skills(plan, paths, paths.root / ".agents" / "skills", "codex")
    return plan


def missing_hooks(paths: ProjectPaths) -> list[str]:
    """The Jotta hook events missing from the project's Codex hooks, when the project uses Codex."""
    if not codex_dir(paths).is_dir():
        return []
    return missing_hook_events(codex_dir(paths) / "hooks.json", HOOKS)
