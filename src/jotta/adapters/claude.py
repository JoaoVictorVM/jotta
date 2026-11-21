"""Generate the Claude Code configuration of a project from its harness files.

The adapter writes three things under ``.claude/``:

- ``settings.json`` gets the ``jotta hook`` commands, merged into any existing settings without removing or
  duplicating entries;
- ``agents/<name>.md`` gets one subagent per role in ``.jotta/agents/``, with read-only tools for the reviewers;
- ``skills/<name>/SKILL.md`` gets one entry per skill in ``.jotta/skills/``, pointing back to the canonical file so
  its references keep resolving and there is only one copy to maintain.
"""

from __future__ import annotations

from pathlib import Path

from jotta.adapters.common import (
    AdapterPlan,
    HookSpec,
    apply_adapter,
    first_paragraph,
    frontmatter,
    marker,
    merge_hooks,
    missing_hook_events,
    split_frontmatter,
    stage,
    stage_hooks,
    stage_skills,
)
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict

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


def plan_adapter(paths: ProjectPaths) -> AdapterPlan:
    """Compute the Claude Code configuration of a project without touching the disk."""
    plan = AdapterPlan(root=paths.root)
    target = claude_dir(paths)
    stage_hooks(plan, target / "settings.json", HOOKS, paths)
    for source in sorted((paths.harness / "agents").glob("*.md")):
        stage(plan, target / "agents" / source.name, agent_file(source, paths))
    stage_skills(plan, paths, target / "skills", "claude")
    return plan


def missing_hooks(paths: ProjectPaths) -> list[str]:
    """The Jotta hook events missing from the project's Claude Code settings."""
    return missing_hook_events(claude_dir(paths) / "settings.json", HOOKS)
