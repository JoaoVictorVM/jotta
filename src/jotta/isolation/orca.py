"""Version-aware Orca adapter for harness-managed worktrees."""

from __future__ import annotations

import argparse
import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path

from jotta.core.state import JSONDict, print_json

EXIT_BLOCKED = 2
CLI_NAMES = ("orca", "orca-dev", "orca-ide")


class OrcaError(RuntimeError):
    pass


def available() -> bool:
    return any(shutil.which(name) for name in CLI_NAMES)


def command_prefix() -> list[str]:
    configured = os.environ.get("ORCA_CLI_COMMAND", "").strip()
    if configured:
        parts = shlex.split(configured, posix=platform.system() != "Windows")
    elif os.environ.get("ORCA_DEV_REPO_ROOT"):
        parts = ["orca-dev"]
    elif platform.system() == "Linux":
        parts = ["orca-ide"]
    else:
        parts = ["orca"]
    if not shutil.which(parts[0]) and not Path(parts[0]).exists():
        raise OrcaError(f"Orca CLI unavailable: {parts[0]} was not found")
    return parts


def invoke(arguments: list[str], check: bool = True) -> JSONDict:
    process = subprocess.run(
        [*command_prefix(), *arguments, "--json"],
        text=True,
        capture_output=True,
        check=False,
    )
    if check and process.returncode != 0:
        detail = (process.stderr or process.stdout).strip()
        raise OrcaError(detail or f"Orca exited with {process.returncode}")
    try:
        payload: JSONDict = json.loads(process.stdout)
    except json.JSONDecodeError as exc:
        raise OrcaError(f"Invalid Orca JSON: {exc}") from exc
    return payload


def load_guide() -> JSONDict:
    return invoke(["skills", "get", "orca-cli"])


def create_worktree(
    name: str,
    agent: str,
    prompt: str,
    model: str | None = None,
    effort: str | None = None,
) -> JSONDict:
    load_guide()
    args = [
        "worktree",
        "create",
        "--name",
        name,
        "--no-parent",
        "--agent",
        agent,
        "--surface",
        "terminal",
        "--activate",
        "--prompt",
        prompt,
    ]
    if model:
        args.extend(["--model", model])
    if effort:
        args.extend(["--effort", effort])
    payload = invoke(args)
    result = payload.get("result", payload)
    launch = result.get("launch", {})
    outcome = launch.get("outcome", {})
    return {
        "raw": payload,
        "worktree_id": result.get("id") or result.get("worktreeId"),
        "worktree_path": result.get("path") or result.get("worktreePath"),
        "branch": result.get("branch"),
        "worker_handle": outcome.get("handle") or result.get("agentTerminalHandle"),
        "surface": outcome.get("kind", "terminal"),
        "prompt_outcome": launch.get("prompt", {}).get("outcome"),
    }


def cleanup(worktree_id: str) -> JSONDict:
    load_guide()
    closed = invoke(["terminal", "close", "--worktree", worktree_id, "--all"])
    removed = invoke(["worktree", "rm", "--worktree", worktree_id])
    return {"terminals": closed, "worktree": removed}


def run(args: argparse.Namespace) -> int:
    """Dispatch a ``jotta orca`` subcommand."""
    try:
        if args.orca_command == "guide":
            output = load_guide()
        elif args.orca_command == "create":
            output = create_worktree(args.name, args.agent, args.prompt, args.model, args.effort)
        else:
            output = cleanup(args.worktree)
    except OrcaError as exc:
        print_json({"status": "blocked", "error": str(exc)}, indent=None)
        return EXIT_BLOCKED
    print_json(output)
    return 0
