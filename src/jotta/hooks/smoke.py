"""Run the fast quality profile after the agent edits code, at most once per debounce window.

A burst of edits triggers one run: an edit inside the window is marked as pending instead of running the profile
again, and the next edit after the window runs it. After a failure the window is ignored, so each fix is checked at
once. Only the compact receipt reaches the agent, and only on failure.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, write_json_atomic
from jotta.quality.runner import execute_profile

EDIT_TOOLS = {"Edit", "MultiEdit", "Write", "NotebookEdit"}
NON_CODE_SUFFIXES = {".md", ".mdx", ".txt", ".rst", ".log", ".csv"}
NON_CODE_DIRECTORIES = {".planning", ".jotta", ".git"}
DEFAULT_SETTINGS: JSONDict = {"profile": "smoke", "debounce_seconds": 20}
MAX_RECEIPT_LINES = 20


@dataclass(frozen=True)
class SmokeOutcome:
    status: str
    message: str | None = None


def settings(paths: ProjectPaths) -> JSONDict:
    configured = load_json(paths.gates, {}).get("post_edit") or {}
    return {**DEFAULT_SETTINGS, **configured}


def is_code(path: str) -> bool:
    pure = PurePosixPath(path.replace("\\", "/"))
    if NON_CODE_DIRECTORIES & set(pure.parts):
        return False
    return pure.suffix.lower() not in NON_CODE_SUFFIXES


def state_path(paths: ProjectPaths) -> Path:
    return paths.state / "post-edit.json"


def failure_message(result: JSONDict) -> str:
    failed: JSONDict = next((item for item in result.get("commands", []) if item.get("exit_code")), {})
    lines = [
        f"The {result.get('profile')} quality profile failed after this edit.",
        f"Command: {failed.get('command')} (exit {failed.get('exit_code')})",
        *[f"  {line}" for line in failed.get("summary", [])[:MAX_RECEIPT_LINES]],
        f"Full log: {failed.get('full_log')}. Receipt: {result.get('receipt')}.",
        "Fix the failure before continuing.",
    ]
    return "\n".join(lines)


def after_edit(payload: JSONDict, paths: ProjectPaths, clock: float | None = None) -> SmokeOutcome:
    """Run the post-edit profile for an edit event, honoring the debounce window."""
    tool_input = payload.get("tool_input")
    if payload.get("tool_name") not in EDIT_TOOLS or not isinstance(tool_input, dict):
        return SmokeOutcome("ignored")
    target = str(tool_input.get("file_path") or tool_input.get("notebook_path") or "")
    if not target or not is_code(target):
        return SmokeOutcome("ignored")
    current = time.time() if clock is None else clock
    state = load_json(state_path(paths), {})
    state["last_edit_at"] = current
    config = settings(paths)
    profile = str(config["profile"])
    commands = load_json(paths.gates, {}).get("profiles", {}).get(profile)
    if not commands:
        write_json_atomic(state_path(paths), state)
        return SmokeOutcome("not-configured")

    last = float(state.get("last_run_at") or 0.0)
    recovering = state.get("status") == "failed"
    if not recovering and current - last < float(config["debounce_seconds"]):
        state["pending"] = True
        write_json_atomic(state_path(paths), state)
        return SmokeOutcome("debounced")

    result, code = execute_profile(paths, profile)
    write_json_atomic(
        state_path(paths),
        {
            "last_edit_at": current,
            "last_run_at": current,
            "pending": False,
            "status": result.get("status"),
            "receipt": result.get("receipt"),
        },
    )
    if code == 0:
        return SmokeOutcome("passed")
    return SmokeOutcome("failed", failure_message(result))
