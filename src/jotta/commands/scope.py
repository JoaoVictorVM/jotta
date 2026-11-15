"""Show and widen the edit scope of the active task.

Widening is a human decision: the ``PreToolUse`` guard refuses ``jotta scope allow`` when an agent runs it, so the
command only takes effect when a person types it.
"""

from __future__ import annotations

import argparse
import json

from jotta.core.paths import ProjectPaths
from jotta.core.scope import ALWAYS_ALLOWED, normalize, unique
from jotta.core.state import JSONDict, default_run, load_json, now, print_json, write_json_atomic

EXIT_INVALID = 2


def active_packet(paths: ProjectPaths) -> tuple[JSONDict, JSONDict] | None:
    """The current run and its context packet, when a task has been prepared."""
    run = load_json(paths.run, default_run())
    packet_path = run.get("context_packet")
    if not packet_path or not (paths.root / packet_path).is_file():
        return None
    return run, load_json(paths.root / packet_path)


def summary(run: JSONDict, packet: JSONDict) -> JSONDict:
    return {
        "task": run.get("current_task"),
        "context_packet": run.get("context_packet"),
        "enforcement": packet.get("scope_enforcement", "off"),
        "allowed_paths": packet.get("allowed_paths", []),
        "always_allowed": list(ALWAYS_ALLOWED),
        "additions": packet.get("scope_additions", []),
    }


def run(paths: ProjectPaths, args: argparse.Namespace) -> int:
    """Dispatch ``jotta scope show`` and ``jotta scope allow``."""
    active = active_packet(paths)
    if active is None:
        print(json.dumps({"status": "invalid", "error": "no prepared task; run jotta prepare first"}))
        return EXIT_INVALID
    current_run, packet = active
    if args.scope_command == "allow":
        added = unique([normalize(path) for path in args.paths])
        if not added:
            print(json.dumps({"status": "invalid", "error": "no path to allow"}))
            return EXIT_INVALID
        packet["allowed_paths"] = unique([*packet.get("allowed_paths", []), *added])
        packet.setdefault("scope_additions", []).append({"paths": added, "reason": args.reason, "at": now()})
        write_json_atomic(paths.root / current_run["context_packet"], packet)
    print_json({"status": "ok", **summary(current_run, packet)})
    return 0
