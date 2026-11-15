"""Check that an edit stays inside the files the active task declared."""

from __future__ import annotations

from pathlib import Path

from jotta.commands.scope import active_packet
from jotta.core.paths import ProjectPaths
from jotta.core.scope import in_scope
from jotta.core.state import JSONDict
from jotta.hooks.guard import ALLOW, Decision

EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
ACTIVE_STATUSES = {"preparing", "running"}
RULE = "edit-outside-task-scope"


def bases(paths: ProjectPaths, run: JSONDict) -> list[Path]:
    """Directories that hold the task's checkout: the project and any worktree a worker uses."""
    found = [paths.root]
    for worker in run.get("workers") or []:
        worktree = worker.get("worktree_path") if isinstance(worker, dict) else None
        if worktree:
            found.append(Path(str(worktree)).resolve())
    return found


def relative_to_checkout(target: Path, checkouts: list[Path]) -> str | None:
    for base in checkouts:
        if target == base or base in target.parents:
            return target.relative_to(base).as_posix()
    return None


def check(payload: JSONDict, paths: ProjectPaths) -> Decision:
    """Block (strict) or warn about (lean) an edit outside the active task's allowed paths."""
    if payload.get("tool_name") not in EDIT_TOOLS:
        return ALLOW
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ALLOW
    raw = tool_input.get("file_path") or tool_input.get("notebook_path")
    active = active_packet(paths)
    if not raw or active is None:
        return ALLOW
    run, packet = active
    enforcement = packet.get("scope_enforcement", "off")
    allowed = packet.get("allowed_paths") or []
    if run.get("status") not in ACTIVE_STATUSES or enforcement == "off" or not allowed:
        return ALLOW
    cwd = Path(str(payload.get("cwd") or paths.root))
    target = (cwd / str(raw)).resolve()
    relative = relative_to_checkout(target, bases(paths, run))
    if relative is None or in_scope(relative, allowed):
        return ALLOW
    reason = (
        f"{relative!r} is outside the files declared for task {run.get('current_task')}; "
        "ask the user to run 'jotta scope allow <path>' if the change is needed"
    )
    return Decision(allowed=enforcement != "block", rule=RULE, reason=reason)
