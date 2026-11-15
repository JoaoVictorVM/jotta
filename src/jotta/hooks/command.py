"""The ``jotta hook`` command: read an agent hook event from stdin and answer with an exit code.

The protocol follows Claude Code hooks. Exit code 0 lets the tool call run, exit code 2 blocks it and shows the
message on stderr to the agent, and any other code reports a hook error without blocking. A warning lets the call
run and prints a ``systemMessage`` on stdout for the user.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TextIO

from jotta.core.paths import ProjectNotFoundError, ProjectPaths, find_root
from jotta.core.state import JSONDict, now
from jotta.hooks import scope
from jotta.hooks.guard import Decision, evaluate

EXIT_ALLOW = 0
EXIT_ERROR = 1
EXIT_BLOCK = 2
EVENTS = ("pre-tool-use",)
LOG_NAME = "hooks.jsonl"
MAX_LOGGED_CHARS = 500


def project_root(payload: JSONDict, explicit: str | None) -> tuple[Path, ProjectPaths | None]:
    """The directory the guard protects and, when it holds a harness, its project paths."""
    if explicit:
        root = Path(explicit).resolve()
        return root, ProjectPaths(root)
    cwd = Path(str(payload.get("cwd") or Path.cwd())).resolve()
    try:
        root = find_root(cwd)
    except ProjectNotFoundError:
        return cwd, None
    return root, ProjectPaths(root)


def log_decision(paths: ProjectPaths, event: str, payload: JSONDict, decision: Decision) -> None:
    tool_input = payload.get("tool_input") or {}
    summary = json.dumps(tool_input, ensure_ascii=False)[:MAX_LOGGED_CHARS]
    record = {
        "time": now(),
        "event": event,
        "session_id": payload.get("session_id"),
        "tool": payload.get("tool_name"),
        "input": summary,
        "decision": "warn" if decision.allowed else "block",
        "rule": decision.rule,
        "reason": decision.reason,
    }
    logs = paths.runtime / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / LOG_NAME).open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def handle(event: str, stream: TextIO, explicit_root: str | None = None) -> int:
    try:
        payload = json.loads(stream.read() or "{}")
    except json.JSONDecodeError as exc:
        print(f"jotta hook: invalid event JSON: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if not isinstance(payload, dict):
        print("jotta hook: the event must be a JSON object", file=sys.stderr)
        return EXIT_ERROR
    root, paths = project_root(payload, explicit_root)
    decision = evaluate(payload, root)
    if decision.allowed and paths is not None:
        decision = scope.check(payload, paths)
    if decision.allowed and decision.rule is None:
        return EXIT_ALLOW
    if paths is not None:
        try:
            log_decision(paths, event, payload, decision)
        except OSError as exc:
            print(f"jotta hook: could not write the hook log: {exc}", file=sys.stderr)
    if decision.allowed:
        print(json.dumps({"systemMessage": f"Jotta warning ({decision.rule}): {decision.reason}."}))
        return EXIT_ALLOW
    print(f"Blocked by the Jotta policy ({decision.rule}): {decision.reason}.", file=sys.stderr)
    return EXIT_BLOCK


def run(args: argparse.Namespace) -> int:
    """Dispatch ``jotta hook <event>``."""
    return handle(args.event, sys.stdin, args.root)
