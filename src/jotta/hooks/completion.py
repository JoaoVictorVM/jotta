"""Keep the agent from ending its turn while the active task lacks a passing quality receipt.

A receipt counts when it comes from the profile the task's profile requires, or a stronger one, passed (or was
skipped because the profile has no commands), and was written after the task was prepared and after the last code
edit. After a few refusals in a row the agent may stop, but the run is marked ``blocked`` so the task is never
recorded as done without its gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from jotta.commands.scope import active_packet
from jotta.core.paths import ProjectPaths
from jotta.core.state import JSONDict, load_json, now, write_json_atomic
from jotta.hooks.smoke import state_path as post_edit_state_path

ACTIVE_STATUSES = {"preparing", "running"}
ACTIVE_STAGES = {"prepared", "implementing", "validating"}
STRENGTH = {"smoke": 1, "feature": 2, "full": 3}
DEFAULT_COMPLETION: JSONDict = {
    "profiles": {"lean": "smoke", "strict": "feature", "manual-classic": "feature"},
    "max_consecutive_blocks": 3,
}
ACCEPTED_STATUSES = {"passed", "skipped"}


@dataclass(frozen=True)
class StopOutcome:
    status: str
    message: str | None = None


def settings(paths: ProjectPaths, gates: JSONDict | None = None) -> JSONDict:
    configured = (load_json(paths.gates, {}) if gates is None else gates).get("completion") or {}
    profiles = {**DEFAULT_COMPLETION["profiles"], **(configured.get("profiles") or {})}
    return {**DEFAULT_COMPLETION, **configured, "profiles": profiles}


def accepted_profiles(required: str) -> set[str]:
    minimum = STRENGTH.get(required)
    if minimum is None:
        return {required}
    return {name for name, strength in STRENGTH.items() if strength >= minimum}


def latest_receipt(paths: ProjectPaths, profiles: set[str], since: float) -> tuple[JSONDict, Path] | None:
    """The newest receipt of one of ``profiles`` written at or after ``since``."""
    folder = paths.runtime / "receipts"
    if not folder.is_dir():
        return None
    candidates: list[tuple[float, JSONDict, Path]] = []
    for path in folder.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        written = path.stat().st_mtime
        if data.get("profile") in profiles and written >= since:
            candidates.append((written, data, path))
    if not candidates:
        return None
    _, data, path = max(candidates, key=lambda item: item[0])
    return data, path


def stop_state_path(paths: ProjectPaths) -> Path:
    return paths.state / "stop-hook.json"


def missing_message(task: str, required: str, receipt: JSONDict | None) -> str:
    if receipt is None:
        problem = f"has no `{required}` quality receipt since it was prepared or since its last code edit"
    elif receipt.get("status") in ACCEPTED_STATUSES:
        problem = (
            f"has a `{receipt.get('profile')}` quality receipt whose commands differ from the committed quality "
            "gates; an uncommitted edit to gates.json does not change the required checks"
        )
    else:
        problem = f"has a `{receipt.get('profile')}` quality receipt with status `{receipt.get('status')}`"
    return "\n".join(
        [
            f"Task {task} is still active and {problem}.",
            f"Run `jotta quality {required}` and fix any failure before finishing.",
            "If the task cannot be completed, record it with `jotta checkpoint --status blocked --blocker <reason>`.",
        ]
    )


def ran_pinned_commands(receipt: JSONDict, gates: JSONDict) -> bool:
    """Whether a receipt ran exactly the commands its profile has in the gates the hooks enforce."""
    expected = (gates.get("profiles") or {}).get(receipt.get("profile")) or []
    ran = [item.get("command") for item in receipt.get("commands") or [] if isinstance(item, dict)]
    return ran == expected


def before_stop(paths: ProjectPaths, gates: JSONDict | None = None) -> StopOutcome:
    """Decide whether the agent may stop now.

    ``gates`` is the configuration the hooks pin; without it the file on disk is read. A receipt whose commands
    differ from the pinned profile, for example after an uncommitted edit that emptied it, does not count.
    """
    active = active_packet(paths)
    if active is None:
        return StopOutcome("no-task")
    run, _packet = active
    if run.get("status") not in ACTIVE_STATUSES or run.get("stage") not in ACTIVE_STAGES:
        return StopOutcome("no-task")
    gates = load_json(paths.gates, {}) if gates is None else gates
    config = settings(paths, gates)
    task = str(run.get("current_task"))
    required = config["profiles"].get(str(run.get("profile")))
    if not required:
        return StopOutcome("not-required")

    packet_file = paths.root / str(run["context_packet"])
    last_edit = float(load_json(post_edit_state_path(paths), {}).get("last_edit_at") or 0.0)
    since = max(packet_file.stat().st_mtime, last_edit)
    found = latest_receipt(paths, accepted_profiles(str(required)), since)
    receipt = found[0] if found else None

    stop_state = load_json(stop_state_path(paths), {})
    if receipt is not None and receipt.get("status") in ACCEPTED_STATUSES and ran_pinned_commands(receipt, gates):
        write_json_atomic(stop_state_path(paths), {"task": task, "blocks": 0})
        return StopOutcome("satisfied")

    blocks = int(stop_state.get("blocks", 0)) + 1 if stop_state.get("task") == task else 1
    if blocks > int(config["max_consecutive_blocks"]):
        run.update(
            {
                "status": "blocked",
                "blocker": f"stopped without a passing `{required}` quality receipt",
                "updated_at": now(),
            }
        )
        write_json_atomic(paths.run, run)
        write_json_atomic(stop_state_path(paths), {"task": task, "blocks": 0})
        return StopOutcome("released-blocked")
    write_json_atomic(stop_state_path(paths), {"task": task, "blocks": blocks})
    return StopOutcome("blocked", missing_message(task, str(required), receipt))
