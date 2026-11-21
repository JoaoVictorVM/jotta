"""Bring hook events from different agents to the shape the checks read.

The checks read Claude Code events: ``Bash`` with a ``command`` string, and file tools with a ``file_path``. Codex
sends a shell command that may be an argument list, and edits files through ``apply_patch``, whose input is a patch
that can touch several files. Each file in a patch becomes its own event: ``Write`` for an added file or a move
destination, ``Edit`` for an updated, deleted or moved file.
"""

from __future__ import annotations

import re
import shlex

from jotta.core.state import JSONDict

PATCH_TOOLS = {"apply_patch"}
PATCH_MARKER = "*** Begin Patch"
PATCH_LINE = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+?)\s*$", re.M)
PATCH_TOOL_FOR = {"Add File": "Write", "Move to": "Write", "Update File": "Edit", "Delete File": "Edit"}
SHELL_FLAGS = {"-c", "-lc", "-ic", "/c", "-Command", "-command"}


def patch_text(tool_input: object) -> str:
    """The patch inside an ``apply_patch`` input, wherever the agent put it."""
    if isinstance(tool_input, str):
        return tool_input if PATCH_MARKER in tool_input else ""
    if isinstance(tool_input, dict):
        values: list[object] = list(tool_input.values())
    elif isinstance(tool_input, list):
        values = list(tool_input)
    else:
        return ""
    return next((text for value in values if (text := patch_text(value))), "")


def patch_files(text: str) -> list[tuple[str, str]]:
    """``(tool, path)`` for every file a patch touches, in order."""
    return [(PATCH_TOOL_FOR[action], path) for action, path in PATCH_LINE.findall(text)]


def shell_command(value: object) -> str:
    """A shell command as one string; ``["bash", "-lc", "script"]`` becomes ``script``."""
    if isinstance(value, list):
        parts = [str(part) for part in value]
        for index, part in enumerate(parts[:-1]):
            if part in SHELL_FLAGS:
                return parts[index + 1]
        return shlex.join(parts)
    return str(value or "")


def expand(payload: JSONDict) -> list[JSONDict]:
    """The events the checks should see for one hook event."""
    tool = payload.get("tool_name")
    tool_input = payload.get("tool_input")
    if tool in PATCH_TOOLS:
        files = patch_files(patch_text(tool_input))
        return [{**payload, "tool_name": name, "tool_input": {"file_path": path}} for name, path in files]
    if tool == "Bash" and isinstance(tool_input, dict) and "command" not in tool_input and "cmd" in tool_input:
        return [{**payload, "tool_input": {**tool_input, "command": shell_command(tool_input["cmd"])}}]
    if tool == "Bash" and isinstance(tool_input, dict) and isinstance(tool_input.get("command"), list):
        return [{**payload, "tool_input": {**tool_input, "command": shell_command(tool_input["command"])}}]
    return [payload]
