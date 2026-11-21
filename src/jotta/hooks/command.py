"""The ``jotta hook`` command: read an agent hook event from stdin and answer in that agent's protocol.

Each event handler decides to allow, warn or block. ``render`` turns that answer into the agent's protocol:

- Claude Code: exit code 0 allows, exit code 2 blocks and shows the message on stderr to the agent, and a warning
  prints a ``systemMessage`` on stdout for the user.
- Codex: every answer exits with code 0 and a JSON object on stdout. ``PreToolUse`` blocks with a ``deny``
  permission decision, ``PostToolUse`` and ``Stop`` block with ``"decision": "block"``, whose reason Codex feeds
  back to the agent.

Any other exit code reports a hook error without blocking.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TextIO

from jotta.core.paths import ProjectNotFoundError, ProjectPaths, find_root
from jotta.core.state import JSONDict, now
from jotta.hooks import completion, scope, smoke
from jotta.hooks.guard import Decision, evaluate
from jotta.hooks.payload import expand

EXIT_ALLOW = 0
EXIT_ERROR = 1
EXIT_BLOCK = 2
EVENTS = ("pre-tool-use", "post-tool-use", "stop")
AGENTS = ("claude", "codex")
LOG_NAME = "hooks.jsonl"
MAX_LOGGED_CHARS = 500


@dataclass(frozen=True)
class Answer:
    """What a hook decided: ``allow``, ``warn`` (allow and tell the user) or ``block``."""

    action: str = "allow"
    message: str = ""


ALLOW = Answer()


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


def try_log(paths: ProjectPaths, event: str, payload: JSONDict, decision: Decision) -> None:
    try:
        log_decision(paths, event, payload, decision)
    except OSError as exc:
        print(f"jotta hook: could not write the hook log: {exc}", file=sys.stderr)


def stop(payload: JSONDict, paths: ProjectPaths | None) -> Answer:
    """Refuse to end the turn while the active task lacks a passing quality receipt."""
    if paths is None:
        return ALLOW
    outcome = completion.before_stop(paths)
    if outcome.status not in {"blocked", "released-blocked"}:
        return ALLOW
    allowed = outcome.status == "released-blocked"
    reason = outcome.message or "the agent stopped repeatedly without a passing quality receipt; run marked blocked"
    try_log(paths, "stop", payload, Decision(allowed=allowed, rule="quality-receipt-required", reason=reason))
    if allowed:
        return Answer("warn", f"Jotta warning (quality-receipt-required): {reason}.")
    return Answer("block", reason)


def post_tool_use(payload: JSONDict, paths: ProjectPaths | None) -> Answer:
    """Run the post-edit quality profile once for the edited files; a failure goes back to the agent."""
    if paths is None:
        return ALLOW
    for event in expand(payload):
        outcome = smoke.after_edit(event, paths)
        if outcome.status == "failed":
            return Answer("block", outcome.message or "the post-edit quality profile failed")
        if outcome.status != "ignored":
            return ALLOW
    return ALLOW


def pre_tool_use(payload: JSONDict, root: Path, paths: ProjectPaths | None) -> Answer:
    """Check every action of the tool call; the first block wins, otherwise the first warning is reported."""
    warning: Answer | None = None
    for event in expand(payload):
        decision = evaluate(event, root)
        if decision.allowed and paths is not None:
            decision = scope.check(event, paths)
        if decision.allowed and decision.rule is None:
            continue
        if paths is not None:
            try_log(paths, "pre-tool-use", event, decision)
        if not decision.allowed:
            return Answer("block", f"Blocked by the Jotta policy ({decision.rule}): {decision.reason}.")
        warning = warning or Answer("warn", f"Jotta warning ({decision.rule}): {decision.reason}.")
    return warning or ALLOW


def render(answer: Answer, event: str, agent: str) -> int:
    """Write ``answer`` in the protocol of ``agent`` and return the exit code."""
    if answer.action == "warn":
        print(json.dumps({"systemMessage": answer.message}))
        return EXIT_ALLOW
    if agent == "codex":
        if answer.action == "block" and event == "pre-tool-use":
            output: JSONDict = {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": answer.message,
                }
            }
            print(json.dumps(output, ensure_ascii=False))
        elif answer.action == "block":
            print(json.dumps({"decision": "block", "reason": answer.message}, ensure_ascii=False))
        elif event == "stop":
            print("{}")
        return EXIT_ALLOW
    if answer.action == "block":
        print(answer.message, file=sys.stderr)
        return EXIT_BLOCK
    return EXIT_ALLOW


def handle(event: str, stream: TextIO, explicit_root: str | None = None, agent: str = "claude") -> int:
    try:
        payload = json.loads(stream.read() or "{}")
    except json.JSONDecodeError as exc:
        print(f"jotta hook: invalid event JSON: {exc}", file=sys.stderr)
        return EXIT_ERROR
    if not isinstance(payload, dict):
        print("jotta hook: the event must be a JSON object", file=sys.stderr)
        return EXIT_ERROR
    root, paths = project_root(payload, explicit_root)
    try:
        if event == "post-tool-use":
            answer = post_tool_use(payload, paths)
        elif event == "stop":
            answer = stop(payload, paths)
        else:
            answer = pre_tool_use(payload, root, paths)
    except (OSError, ValueError, KeyError) as exc:
        print(f"jotta hook: the {event} check could not run: {exc}", file=sys.stderr)
        return EXIT_ERROR
    return render(answer, event, agent)


def run(args: argparse.Namespace) -> int:
    """Dispatch ``jotta hook <event>``."""
    return handle(args.event, sys.stdin, args.root, args.agent)
